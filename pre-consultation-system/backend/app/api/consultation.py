import uuid
import json
import re
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.api.auth import get_current_user
from app.logger import logger
from app.schemas.consultation import (
    StartConsultationRequest,
    AnswerRequest,
    RecommendResult,
    RegistrationRequest,
)
from app.models.consultation_session import ConsultationSession, SessionStatus
from app.models.question_record import QuestionRecord, AnswerType
from app.models.registration import Registration, TimeSlot, RegistrationStatus
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.symptom_dict import SymptomDict
from app.services.symptom_standardizer import standardize_symptoms
from app.services.extraction_service import extract_from_description
from app.services.reasoning_engine import (
    calculate_disease_scores,
    prune_by_required,
    apply_differential_rules,
    select_next_symptom,
    generate_recommendation,
)
from app.services.final_scorer import fuse_scores, degrade_only
from app.services.deepseek_client import is_available, rank_diseases

router = APIRouter(dependencies=[Depends(get_current_user)])


def _build_question_text(symptom_name: str) -> str:
    return f"您是否有「{symptom_name}」的症状？"


async def _fuse_candidates(candidates: list[dict], collected_data: dict) -> list[dict]:
    """用 DeepSeek 重新排序候选疾病并融合评分，不可用时降级为规则引擎"""
    if is_available():
        symptoms = list(collected_data.get("symptoms", {}).keys()) if collected_data else []
        ds_result = await rank_diseases(symptoms, candidates, collected_data)
        ds_rankings = ds_result.get("rankings", [])
        fusion = fuse_scores(candidates, ds_rankings)
    else:
        fusion = degrade_only(candidates)
    return [{
        "disease_id": m["disease_id"],
        "disease_name": m["disease_name"],
        "score": m["final_score"],
        "department_id": m["department_id"],
        "department_name": m["department_name"],
        "urgency": m["urgency"],
    } for m in fusion["merged"]]


@router.post("/start")
async def start_consultation(req: StartConsultationRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())

    symptom_matches = []
    if req.description:
        desc_matches = extract_from_description(req.description, db)
        symptom_matches.extend(desc_matches)
    for raw in req.symptoms:
        matches = standardize_symptoms(raw, db)
        if matches:
            symptom_matches.extend(matches)

    symptom_names = list({m["symptom_name"] for m in symptom_matches})
    logger.info("开始问诊 session=%s, patient=%s, 初始症状=%s", session_id, current_user["username"], symptom_names)
    if not symptom_names:
        logger.warning("问诊启动失败: 未识别到有效症状, patient=%s", current_user["username"])
        raise HTTPException(status_code=400, detail="未能识别任何有效症状")

    collected_data = {
        "symptoms": {name: True for name in symptom_names},
        "onset_days": None,
        "severity": req.severity,
        "medical_history": req.medical_history or [],
        "current_medications": req.current_medications or [],
        "allergies": req.allergies or [],
    }

    if req.onset_date:
        try:
            onset = date.fromisoformat(req.onset_date)
            collected_data["onset_days"] = (date.today() - onset).days
        except ValueError:
            pass

    if req.duration:
        m = re.match(r'(\d+)\s*(天|周|个月|日)', req.duration)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if unit in ('周',):
                collected_data["onset_days"] = n * 7
            elif unit in ('个月',):
                collected_data["onset_days"] = n * 30
            else:
                collected_data["onset_days"] = n
        else:
            collected_data["duration_text"] = req.duration

    candidates = calculate_disease_scores(collected_data, db)
    candidates = prune_by_required(candidates)
    candidates = apply_differential_rules(candidates, collected_data, db)
    candidates = await _fuse_candidates(candidates, collected_data)

    session = ConsultationSession(
        id=session_id,
        patient_id=current_user["username"],
        status=SessionStatus.QUESTIONING,
        current_round=0,
        collected_data=collected_data,
        candidate_diseases=[{
            "disease_id": c["disease_id"],
            "disease_name": c["disease_name"],
            "score": c["score"],
        } for c in candidates[:20]],
        asked_symptoms=symptom_names,
    )
    db.add(session)
    db.commit()

    next_symptom = select_next_symptom(candidates, symptom_names, db)
    if next_symptom:
        session.current_round = 1
        question_text = _build_question_text(next_symptom["symptom_name"])
        record = QuestionRecord(
            consultation_id=session_id,
            round=1,
            symptom_id=next_symptom["symptom_id"],
            question_text=question_text,
        )
        db.add(record)
        db.commit()

        return {
            "consultation_id": session_id,
            "question_id": record.id,
            "question_text": question_text,
            "symptom_id": next_symptom["symptom_id"],
            "round": 1,
            "total_rounds": settings.MAX_QUESTION_ROUNDS,
        }

    session.status = SessionStatus.RECOMMENDING
    result = generate_recommendation(candidates, collected_data)
    session.final_recommendation = result
    db.commit()

    logger.info("问诊直接出推荐结果 session=%s, 候选疾病数=%d", session_id, len(candidates))
    return {
        "consultation_id": session_id,
        "message": "直接生成推荐",
        "result": result,
    }


@router.post("/{consultation_id}/answer")
async def answer_question(consultation_id: str, req: AnswerRequest, db: Session = Depends(get_db)):
    session = db.query(ConsultationSession).filter(ConsultationSession.id == consultation_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.status != SessionStatus.QUESTIONING:
        raise HTTPException(status_code=400, detail="当前状态不允许作答")

    if req.answer not in ("YES", "NO", "UNKNOWN"):
        raise HTTPException(status_code=400, detail="答案必须是 YES/NO/UNKNOWN")

    current_round = session.current_round
    record = db.query(QuestionRecord).filter(
        QuestionRecord.consultation_id == consultation_id,
        QuestionRecord.round == current_round,
    ).first()
    if not record:
        raise HTTPException(status_code=400, detail="当前轮次无待回答问题")

    if record.answer is not None:
        raise HTTPException(status_code=400, detail="该问题已经回答过")

    logger.info("回答问诊 session=%s, round=%d, symptom_id=%d, answer=%s", consultation_id, current_round, req.symptom_id, req.answer)
    record.answer = AnswerType(req.answer)
    collected = dict(session.collected_data)
    symptoms = dict(collected.get("symptoms", {}))

    sym = db.query(SymptomDict).filter(SymptomDict.id == req.symptom_id).first()
    if sym:
        if req.answer == "YES":
            symptoms[sym.name] = True
        elif req.answer == "NO":
            symptoms[sym.name] = False
        elif req.answer == "UNKNOWN":
            symptoms[sym.name] = None

    collected["symptoms"] = symptoms
    session.collected_data = collected

    candidates = calculate_disease_scores(collected, db)
    candidates = prune_by_required(candidates)
    candidates = apply_differential_rules(candidates, collected, db)
    candidates = await _fuse_candidates(candidates, collected)

    asked = list(session.asked_symptoms or [])
    if sym:
        asked.append(sym.name)
    session.asked_symptoms = list(set(asked))

    top_count = len([c for c in candidates if c["score"] > 0])
    should_stop = (
        top_count <= settings.CANDIDATE_THRESHOLD
        or current_round >= settings.MAX_QUESTION_ROUNDS
    )

    if should_stop:
        session.status = SessionStatus.RECOMMENDING
        result = generate_recommendation(candidates, collected)
        session.final_recommendation = result
        db.commit()
        logger.info("问诊结束(达到停止条件) session=%s, 候选疾病数=%d", consultation_id, top_count)
        return {
            "status": "RECOMMENDING",
            "result": result,
            "round": current_round,
            "total_rounds": current_round,
        }

    session.current_round += 1
    next_symptom = select_next_symptom(candidates, asked, db)

    if not next_symptom:
        session.status = SessionStatus.RECOMMENDING
        result = generate_recommendation(candidates, collected)
        session.final_recommendation = result
        db.commit()
        logger.info("问诊结束(无更多追问) session=%s", consultation_id)
        return {
            "status": "RECOMMENDING",
            "result": result,
            "round": current_round,
            "total_rounds": current_round,
        }

    question_text = _build_question_text(next_symptom["symptom_name"])
    new_record = QuestionRecord(
        consultation_id=consultation_id,
        round=session.current_round,
        symptom_id=next_symptom["symptom_id"],
        question_text=question_text,
    )
    db.add(new_record)
    db.commit()

    logger.info("追问下一轮 session=%s, round=%d, symptom=%s", consultation_id, session.current_round, next_symptom["symptom_name"])
    return {
        "status": "QUESTIONING",
        "question_id": new_record.id,
        "question_text": question_text,
        "symptom_id": next_symptom["symptom_id"],
        "round": session.current_round,
        "total_rounds": settings.MAX_QUESTION_ROUNDS,
    }


@router.get("/{consultation_id}/result")
def get_result(consultation_id: str, db: Session = Depends(get_db)):
    session = db.query(ConsultationSession).filter(ConsultationSession.id == consultation_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.status not in (SessionStatus.RECOMMENDING, SessionStatus.BOOKING, SessionStatus.COMPLETED):
        return {
            "status": session.status.value,
            "message": "问诊仍在进行中",
            "current_round": session.current_round,
            "asked_symptoms": session.asked_symptoms,
        }

    return {
        "status": session.status.value,
        "result": session.final_recommendation,
    }


@router.post("/registration")
def create_registration(req: RegistrationRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    session = None
    if req.consultation_id:
        session = db.query(ConsultationSession).filter(ConsultationSession.id == req.consultation_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

    dep = db.query(Department).filter(Department.id == req.department_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="科室不存在")

    doctor = db.query(Doctor).filter(Doctor.id == req.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")

    try:
        reg_date = date.fromisoformat(req.registration_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，需要 YYYY-MM-DD")

    time_slots = [s.value for s in TimeSlot]
    if req.time_slot not in time_slots:
        raise HTTPException(status_code=400, detail=f"时段必须是 {', '.join(time_slots)} 之一")

    logger.info("挂号成功 session=%s, patient=%s, dept=%s, doctor=%s, date=%s", req.consultation_id or 'direct', current_user["username"], dep.name, doctor.name, req.registration_date)
    registration = Registration(
        patient_id=current_user["username"],
        consultation_id=req.consultation_id,
        department_id=req.department_id,
        doctor_id=req.doctor_id,
        registration_date=reg_date,
        time_slot=TimeSlot(req.time_slot),
        status=RegistrationStatus.WAITING,
    )
    db.add(registration)
    if session:
        session.status = SessionStatus.BOOKING
    db.commit()

    return {
        "registration_id": registration.id,
        "message": "挂号成功",
        "department": dep.name,
        "doctor_name": doctor.name,
        "date": req.registration_date,
        "time_slot": req.time_slot,
    }


@router.get("/registration/my")
def my_registrations(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient_id = current_user.get("username", "anonymous")
    registrations = (
        db.query(Registration)
        .filter(Registration.patient_id == patient_id)
        .order_by(Registration.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "registration_date": r.registration_date.isoformat(),
            "time_slot": r.time_slot.value,
            "status": r.status.value,
            "department": r.department.name if r.department else "",
            "doctor": r.doctor.name if r.doctor else "",
        }
        for r in registrations
    ]


@router.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    return [{"id": d.id, "name": d.name} for d in db.query(Department).all()]


@router.get("/doctors")
def list_doctors(department_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Doctor)
    if department_id:
        q = q.filter(Doctor.department_id == department_id)
    return [
        {"id": d.id, "name": d.name, "title": d.title, "department_id": d.department_id, "introduction": d.introduction}
        for d in q.all()
    ]


@router.get("/timeslots")
def get_timeslots():
    slots = [s.value for s in TimeSlot]
    result = []
    for v in slots:
        h = int(v.split(":")[0])
        period = "上午" if h < 12 else "下午"
        result.append({"value": v, "period": period})
    return result


@router.get("/timeslots/available")
def available_timeslots(doctor_id: int, registration_date: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")
    try:
        reg_date = date.fromisoformat(registration_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")
    max_total = doctor.max_patients_per_session or 20
    used = {}
    bookings = db.query(Registration).filter(
        Registration.doctor_id == doctor_id,
        Registration.registration_date == reg_date,
    ).all()
    for b in bookings:
        slot = b.time_slot.value if hasattr(b.time_slot, 'value') else b.time_slot
        used[slot] = used.get(slot, 0) + 1
    slots = [s.value for s in TimeSlot]
    return [
        {
            "value": v,
            "period": "上午" if int(v.split(":")[0]) < 12 else "下午",
            "total": max_total,
            "used": used.get(v, 0),
            "remaining": max_total - used.get(v, 0),
        }
        for v in slots
    ]


@router.post("/pipeline-debug")
async def pipeline_debug(req: StartConsultationRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    降解模式全流程调试端点。返回管道的每一步结果。
    """
    from app.config import settings
    from app.services.extraction_service import extract_from_description

    stages = {}
    stages["ai_mode"] = settings.AI_MODE

    stages["symptom_matches"] = []
    if req.description:
        desc_matches = extract_from_description(req.description, db)
        stages["symptom_matches"].extend(desc_matches)
    for raw in req.symptoms:
        matches = standardize_symptoms(raw, db)
        if matches:
            stages["symptom_matches"].extend(matches)

    symptom_names = list({m["symptom_name"] for m in stages["symptom_matches"]})

    collected_data = {
        "symptoms": {name: True for name in symptom_names},
        "onset_days": None,
        "severity": req.severity,
        "medical_history": req.medical_history or [],
        "current_medications": req.current_medications or [],
        "allergies": req.allergies or [],
    }
    if req.duration:
        m = re.match(r'(\d+)\s*(天|周|个月|日)', req.duration)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if unit in ('周',):
                collected_data["onset_days"] = n * 7
            elif unit in ('个月',):
                collected_data["onset_days"] = n * 30
            else:
                collected_data["onset_days"] = n

    stages["collected_data"] = {k: str(v) if isinstance(v, (dict, list)) else v for k, v in collected_data.items()}

    candidates = calculate_disease_scores(collected_data, db)
    stages["initial_candidates"] = [
        {"name": c["disease_name"], "score": c["score"], "dept": c["department_name"], "urgency": c["urgency"]}
        for c in candidates[:10]
    ]

    candidates = prune_by_required(candidates)
    candidates = apply_differential_rules(candidates, collected_data, db)
    stages["after_rules"] = [
        {"name": c["disease_name"], "score": c["score"]}
        for c in candidates[:10]
    ]

    next_s = select_next_symptom(candidates, symptom_names, db)
    stages["next_question"] = next_s

    result = generate_recommendation(candidates, collected_data)
    stages["recommendation"] = result

    from app.services.final_scorer import fuse_scores, degrade_only
    from app.services.deepseek_client import is_available, rank_diseases

    if is_available():
        ds_result = await rank_diseases(symptom_names, candidates, collected_data)
        ds_rankings = ds_result.get("rankings", [])
        ds_ok = "error" not in ds_result
        stages["deepseek_raw"] = {"success": ds_ok, "explanation": ds_result.get("explanation", "")}
        fusion = fuse_scores(candidates, ds_rankings)
    else:
        fusion = degrade_only(candidates)
    stages["final_scorer"] = {
        "mode": fusion.get("mode", "fused"),
        "agreement": fusion["agreement"],
        "conflicts": fusion["conflicts"][:3],
        "merged": [
            {"name": m["disease_name"], "rule": m["rule_score"], "ds": m["ds_score"], "final": m["final_score"]}
            for m in fusion["merged"][:10]
        ],
    }

    return stages


@router.get("/deepseek/health")
async def deepseek_health():
    from app.services.deepseek_client import health_check
    return await health_check()


@router.get("/deepseek/test")
async def deepseek_test():
    from app.services.deepseek_client import is_available, enrich_symptoms
    if not is_available():
        return {"status": "disabled", "message": "请设置 DEEPSEEK_API_KEY 并启用 DEEPSEEK_ENABLED"}
    result = await enrich_symptoms(["发热", "咳嗽"], "最近几天一直不舒服")
    return {"status": "ok", "result": result}
