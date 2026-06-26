import uuid
import json
import re
import asyncio
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.config import settings
from app.api.auth import get_current_user, require_role
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
from app.services.extraction_service import extract_from_description, extract_from_description_async
from app.services.reasoning_engine import (
    calculate_disease_scores,
    prune_by_required,
    apply_differential_rules,
    select_next_symptom,
    generate_recommendation,
)
from app.services.final_scorer import fuse_scores, degrade_only
from app.services.deepseek_client import is_available, rank_diseases, suggest_next_question
from app.services.deepseek_client import (
    extract_and_initial_question,
    next_question as ds_next_question,
    final_recommendation as ds_final_recommendation,
)

router = APIRouter(dependencies=[Depends(get_current_user)])
local_limiter = Limiter(key_func=get_remote_address)


def _build_question_text(symptom_name: str) -> str:
    return f"您是否有「{symptom_name}」的症状？"


async def _fuse_candidates(candidates: list[dict], collected_data: dict) -> list[dict]:
    """用 DeepSeek 重新排序候选疾病并融合评分，不可用时降级为规则引擎"""
    if is_available():
        try:
            symptoms = list(collected_data.get("symptoms", {}).keys()) if collected_data else []
            ds_result = await asyncio.wait_for(rank_diseases(symptoms, candidates, collected_data), timeout=10)
            ds_rankings = ds_result.get("rankings", [])
            fusion = fuse_scores(candidates, ds_rankings)
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning("DeepSeek rank_diseases 超时或失败: %s", e)
            fusion = degrade_only(candidates)
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


async def _select_next_symptom(
    candidates: list[dict],
    collected_data: dict,
    asked_symptoms: list[str],
    db: Session,
) -> dict | None:
    """选择下一个追问症状：优先 DeepSeek 推理，不可用或未命中则回退规则引擎"""
    rule_result = select_next_symptom(candidates, asked_symptoms, db)

    if is_available():
        confirmed = [k for k, v in collected_data.get("symptoms", {}).items() if v is True]
        denied = [k for k, v in collected_data.get("symptoms", {}).items() if v is False]
        try:
            ds = await asyncio.wait_for(
                suggest_next_question(confirmed, denied, candidates, asked_symptoms, collected_data),
                timeout=10,
            )
            ds_name = ds.get("symptom_name", "").strip()
            if ds_name:
                sym = db.query(SymptomDict).filter(SymptomDict.name == ds_name).first()
                if not sym:
                    sym = db.query(SymptomDict).filter(SymptomDict.aliases.like(f"%{ds_name}%")).first()
                if sym:
                    return {
                        "symptom_id": sym.id,
                        "symptom_name": sym.name,
                        "ds_reasoning": ds.get("reasoning", ""),
                    }
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug("DeepSeek 追问超时或失败: %s, 回退规则引擎", e)

    return rule_result


# ============================================================
#  精简线性问诊 — DeepSeek 驱动，一次提取、逐轮收窄
# ============================================================

def _parse_duration(req: StartConsultationRequest) -> int | None:
    """解析病程天数"""
    if req.duration:
        m = re.match(r'(\d+)\s*(天|周|个月|日)', req.duration)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            if unit == '周': return n * 7
            if unit == '个月': return n * 30
            return n
    if req.onset_date:
        try:
            return (date.today() - date.fromisoformat(req.onset_date)).days
        except ValueError:
            pass
    return None


def _init_collected_data(req: StartConsultationRequest, symptom_names: list[str]) -> dict:
    """构建 collected_data 初始结构"""
    return {
        "description": req.description or "",
        "symptoms": {name: True for name in symptom_names},
        "onset_days": _parse_duration(req),
        "severity": req.severity,
        "medical_history": req.medical_history or [],
        "current_medications": req.current_medications or [],
        "allergies": req.allergies or [],
        "conversation": [],
    }


def _record_answer(collected: dict, symptom_name: str, answer: str) -> dict:
    """增量记录本轮回答到 collected_data"""
    conv = list(collected.get("conversation", []))
    conv.append({"symptom": symptom_name, "answer": answer})
    collected["conversation"] = conv
    symptoms = dict(collected.get("symptoms", {}))
    if answer == "YES":
        symptoms[symptom_name] = True
    elif answer == "NO":
        symptoms[symptom_name] = False
    elif answer == "UNKNOWN":
        symptoms[symptom_name] = None
    collected["symptoms"] = symptoms
    return collected


@router.post("/start")
async def start_consultation(
    req: StartConsultationRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = str(uuid.uuid4())

    if is_available():
        # ====== DeepSeek 快速路径 ======
        result = await extract_and_initial_question(
            req.description or "", req.symptoms or [], db
        )
        extracted = result.get("extracted_symptoms", [])
        candidates = result.get("candidate_diseases", [])
        first_q = result.get("question")

        symptom_names = list({s["symptom_name"] for s in extracted})
        # 合并前端标签
        for tag in (req.symptoms or []):
            matches = standardize_symptoms(tag, db)
            for m in matches:
                if m["symptom_name"] not in symptom_names:
                    symptom_names.append(m["symptom_name"])

        logger.info(
            "[DS] 开始问诊 session=%s patient=%s symptoms=%d candidates=%d q=%s",
            session_id, current_user.get("username", "?"),
            len(symptom_names), len(candidates),
            first_q["symptom_name"] if first_q else "(无)",
        )

        if not symptom_names:
            raise HTTPException(
                status_code=400,
                detail="未能从您的描述中识别出有效症状。请用更详细的语言描述。",
            )

        collected_data = _init_collected_data(req, symptom_names)

        session = ConsultationSession(
            id=session_id,
            patient_id=current_user["username"],
            status=SessionStatus.QUESTIONING,
            current_round=0,
            collected_data=collected_data,
            candidate_diseases=candidates,
            asked_symptoms=symptom_names,
        )
        db.add(session)
        db.commit()

        if first_q and first_q.get("symptom_name"):
            session.current_round = 1
            q_text = first_q.get("question_text", _build_question_text(first_q["symptom_name"]))
            record = QuestionRecord(
                consultation_id=session_id, round=1,
                symptom_id=first_q.get("symptom_id"),
                question_text=q_text,
            )
            db.add(record)
            db.commit()
            return {
                "consultation_id": session_id,
                "question_id": record.id,
                "question_text": q_text,
                "symptom_id": first_q.get("symptom_id"),
                "round": 1,
                "total_rounds": settings.MAX_QUESTION_ROUNDS,
                "reasoning": first_q.get("reasoning", ""),
            }

        # 没有追问，直接出结果
        session.status = SessionStatus.RECOMMENDING
        final = await ds_final_recommendation(
            collected_data.get("symptoms", {}), candidates, collected_data, db
        )
        session.final_recommendation = final
        db.commit()
        return {
            "consultation_id": session_id,
            "message": "直接生成推荐",
            "result": final,
        }

    else:
        # ====== 降级路径：旧规则引擎 ======
        symptom_matches = []
        if req.description:
            desc_matches = await extract_from_description_async(req.description, db)
            symptom_matches.extend(desc_matches)
        for raw in req.symptoms:
            matches = standardize_symptoms(raw, db)
            if matches:
                symptom_matches.extend(matches)

        symptom_names = list({m["symptom_name"] for m in symptom_matches})
        logger.info("[降级] 开始问诊 session=%s patient=%s symptoms=%s",
                     session_id, current_user.get("username", "?"), symptom_names)
        if not symptom_names:
            raise HTTPException(
                status_code=400,
                detail="未识别到有效症状。系统未启用AI辅助，请从症状列表手动选择。",
            )

        collected_data = _init_collected_data(req, symptom_names)
        candidates = calculate_disease_scores(collected_data, db)
        candidates = prune_by_required(candidates)
        candidates = apply_differential_rules(candidates, collected_data, db)

        session = ConsultationSession(
            id=session_id, patient_id=current_user["username"],
            status=SessionStatus.QUESTIONING, current_round=0,
            collected_data=collected_data,
            candidate_diseases=[{
                "disease_id": c["disease_id"], "disease_name": c["disease_name"],
                "likelihood": c["score"],
            } for c in candidates[:20]],
            asked_symptoms=symptom_names,
        )
        db.add(session)
        db.commit()

        next_symptom = await _select_next_symptom(candidates, collected_data, symptom_names, db)
        if next_symptom:
            session.current_round = 1
            q_text = _build_question_text(next_symptom["symptom_name"])
            record = QuestionRecord(
                consultation_id=session_id, round=1,
                symptom_id=next_symptom["symptom_id"], question_text=q_text,
            )
            db.add(record)
            db.commit()
            resp = {
                "consultation_id": session_id, "question_id": record.id,
                "question_text": q_text, "symptom_id": next_symptom["symptom_id"],
                "round": 1, "total_rounds": settings.MAX_QUESTION_ROUNDS,
            }
            if next_symptom.get("ds_reasoning"):
                resp["ds_reasoning"] = next_symptom["ds_reasoning"]
            return resp

        session.status = SessionStatus.RECOMMENDING
        result = generate_recommendation(candidates, collected_data)
        session.final_recommendation = result
        db.commit()
        return {"consultation_id": session_id, "message": "直接生成推荐", "result": result}


@router.post("/{consultation_id}/answer")
@local_limiter.limit("10/minute")
async def answer_question(
    consultation_id: str,
    req: AnswerRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 基础校验
    session = db.query(ConsultationSession).filter(
        ConsultationSession.id == consultation_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.patient_id != current_user["username"]:
        raise HTTPException(status_code=403, detail="无权操作他人问诊会话")
    if session.status != SessionStatus.QUESTIONING:
        raise HTTPException(status_code=400, detail="当前状态不允许作答")
    if req.answer not in ("YES", "NO", "UNKNOWN"):
        raise HTTPException(status_code=400, detail="答案必须是 YES/NO/UNKNOWN")

    # 加锁防并发
    session = db.query(ConsultationSession).filter(
        ConsultationSession.id == consultation_id
    ).with_for_update().first()
    if not session or session.status != SessionStatus.QUESTIONING:
        raise HTTPException(status_code=400, detail="当前状态不允许作答")

    current_round = session.current_round
    record = db.query(QuestionRecord).filter(
        QuestionRecord.consultation_id == consultation_id,
        QuestionRecord.round == current_round,
    ).with_for_update().first()
    if not record:
        raise HTTPException(status_code=400, detail="当前轮次无待回答问题")
    if record.answer is not None:
        raise HTTPException(status_code=409, detail="该问题已经回答过")

    sym = db.query(SymptomDict).filter(SymptomDict.id == req.symptom_id).first()
    sym_name = sym.name if sym else ""
    logger.info("回答问诊 session=%s round=%d symptom=%s answer=%s",
                 consultation_id, current_round, sym_name, req.answer)
    record.answer = AnswerType(req.answer)

    if is_available():
        # ====== DeepSeek 快速路径 ======
        collected = dict(session.collected_data)
        collected = _record_answer(collected, sym_name, req.answer)
        collected["current_round"] = current_round
        collected["max_rounds"] = settings.MAX_QUESTION_ROUNDS

        candidates = list(session.candidate_diseases or [])
        asked = list(session.asked_symptoms or []) + [sym_name]
        session.asked_symptoms = list(set(asked))

        confirmed = [k for k, v in collected.get("symptoms", {}).items() if v is True]
        denied = [k for k, v in collected.get("symptoms", {}).items() if v is False]

        result = await ds_next_question(confirmed, denied, asked, candidates, collected, db)

        if result.get("should_stop") or current_round >= settings.MAX_QUESTION_ROUNDS:
            session.status = SessionStatus.RECOMMENDING
            session.collected_data = collected
            final = await ds_final_recommendation(
                collected.get("symptoms", {}), candidates, collected, db
            )
            session.final_recommendation = final
            db.commit()
            logger.info("[DS] 问诊结束 session=%s round=%d", consultation_id, current_round)
            return {
                "status": "RECOMMENDING",
                "result": final,
                "round": current_round,
                "total_rounds": current_round,
            }

        next_q = result.get("question")
        if not next_q or not next_q.get("symptom_name"):
            session.status = SessionStatus.RECOMMENDING
            session.collected_data = collected
            final = await ds_final_recommendation(
                collected.get("symptoms", {}), candidates, collected, db
            )
            session.final_recommendation = final
            db.commit()
            return {
                "status": "RECOMMENDING",
                "result": final,
                "round": current_round,
                "total_rounds": current_round,
            }

        session.current_round += 1
        session.collected_data = collected
        session.candidate_diseases = candidates

        q_text = next_q.get("question_text", _build_question_text(next_q["symptom_name"]))
        new_record = QuestionRecord(
            consultation_id=consultation_id,
            round=session.current_round,
            symptom_id=next_q.get("symptom_id"),
            question_text=q_text,
        )
        db.add(new_record)
        db.commit()

        logger.info("[DS] 追问 session=%s round=%d symptom=%s",
                     consultation_id, session.current_round, next_q["symptom_name"])
        return {
            "status": "QUESTIONING",
            "question_id": new_record.id,
            "question_text": q_text,
            "symptom_id": next_q.get("symptom_id"),
            "round": session.current_round,
            "total_rounds": settings.MAX_QUESTION_ROUNDS,
            "reasoning": next_q.get("reasoning", ""),
        }

    else:
        # ====== 降级路径：旧规则引擎 ======
        collected = dict(session.collected_data)
        symptoms = dict(collected.get("symptoms", {}))
        if req.answer == "YES":
            symptoms[sym_name] = True
        elif req.answer == "NO":
            symptoms[sym_name] = False
        elif req.answer == "UNKNOWN":
            symptoms[sym_name] = None
        collected["symptoms"] = symptoms
        session.collected_data = collected

        candidates = calculate_disease_scores(collected, db)
        candidates = prune_by_required(candidates)
        candidates = apply_differential_rules(candidates, collected, db)
        candidates = await _fuse_candidates(candidates, collected)

        asked = list(session.asked_symptoms or []) + [sym_name]
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
            logger.info("[降级] 问诊结束 session=%s round=%d", consultation_id, current_round)
            return {
                "status": "RECOMMENDING", "result": result,
                "round": current_round, "total_rounds": current_round,
            }

        session.current_round += 1
        next_symptom = await _select_next_symptom(candidates, collected, asked, db)

        if not next_symptom:
            session.status = SessionStatus.RECOMMENDING
            result = generate_recommendation(candidates, collected)
            session.final_recommendation = result
            db.commit()
            return {
                "status": "RECOMMENDING", "result": result,
                "round": current_round, "total_rounds": current_round,
            }

        q_text = _build_question_text(next_symptom["symptom_name"])
        new_record = QuestionRecord(
            consultation_id=consultation_id, round=session.current_round,
            symptom_id=next_symptom["symptom_id"], question_text=q_text,
        )
        db.add(new_record)
        db.commit()

        resp = {
            "status": "QUESTIONING", "question_id": new_record.id,
            "question_text": q_text, "symptom_id": next_symptom["symptom_id"],
            "round": session.current_round, "total_rounds": settings.MAX_QUESTION_ROUNDS,
        }
        if next_symptom.get("ds_reasoning"):
            resp["ds_reasoning"] = next_symptom["ds_reasoning"]
        return resp


@router.get("/{consultation_id}/result")
def get_result(consultation_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(ConsultationSession).filter(ConsultationSession.id == consultation_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.patient_id != current_user["username"]:
        raise HTTPException(status_code=403, detail="无权查看他人问诊结果")
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
        if session.patient_id != current_user["username"]:
            raise HTTPException(status_code=403, detail="无权使用他人问诊会话进行挂号")

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

    registration = Registration(
        patient_id=current_user["username"],
        consultation_id=req.consultation_id or None,
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

    logger.info("挂号成功 session=%s, patient=%s, dept=%s, doctor=%s, date=%s", req.consultation_id or 'direct', current_user["username"], dep.name, doctor.name, req.registration_date)

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
async def pipeline_debug(
    req: StartConsultationRequest,
    current_user: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """DeepSeek 全流程调试端点。返回提取→候选→追问→推荐的每一步结果。"""
    stages = {"ai_mode": settings.AI_MODE}

    if not is_available():
        stages["error"] = "DeepSeek 不可用，无法调试新流程"
        return stages

    # Step 1: 提取+初问
    ds_result = await extract_and_initial_question(
        req.description or "", req.symptoms or [], db
    )
    stages["extraction"] = {
        "symptoms": [
            {"name": s["symptom_name"], "confidence": s.get("confidence")}
            for s in ds_result.get("extracted_symptoms", [])
        ],
        "candidates": [
            {"name": c["disease_name"], "dept": c.get("department_name"), "likelihood": c.get("likelihood")}
            for c in ds_result.get("candidate_diseases", [])
        ],
        "first_question": ds_result.get("question"),
    }

    # Step 2: 模拟终局推荐
    symptom_names = [s["symptom_name"] for s in ds_result.get("extracted_symptoms", [])]
    mock_collected = {
        "symptoms": {n: True for n in symptom_names},
        "severity": req.severity,
        "onset_days": _parse_duration(req),
        "medical_history": req.medical_history or [],
        "current_medications": req.current_medications or [],
        "allergies": req.allergies or [],
    }
    final = await ds_final_recommendation(
        mock_collected.get("symptoms", {}),
        ds_result.get("candidate_diseases", []),
        mock_collected,
        db,
    )
    stages["final_recommendation"] = final

    return stages


@router.get("/deepseek/health")
async def deepseek_health(current_user: dict = Depends(require_role("admin"))):
    from app.services.deepseek_client import health_check
    return await health_check()


@router.get("/deepseek/test")
async def deepseek_test(current_user: dict = Depends(require_role("admin"))):
    from app.services.deepseek_client import is_available, enrich_symptoms
    if not is_available():
        return {"status": "disabled", "message": "请设置 DEEPSEEK_API_KEY 并启用 DEEPSEEK_ENABLED"}
    result = await enrich_symptoms(["发热", "咳嗽"], "最近几天一直不舒服")
    return {"status": "ok", "result": result}
