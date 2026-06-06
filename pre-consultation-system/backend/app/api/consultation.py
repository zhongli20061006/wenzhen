import uuid
import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.api.auth import get_current_user
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
from app.services.reasoning_engine import (
    calculate_disease_scores,
    prune_by_required,
    apply_differential_rules,
    select_next_symptom,
    generate_recommendation,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _build_question_text(symptom_name: str) -> str:
    return f"您是否有「{symptom_name}」的症状？"


@router.post("/start")
def start_consultation(req: StartConsultationRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())

    symptom_matches = []
    for raw in req.symptoms:
        matches = standardize_symptoms(raw, db)
        if matches:
            symptom_matches.extend(matches)

    symptom_names = list({m["symptom_name"] for m in symptom_matches})
    if not symptom_names:
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

    candidates = calculate_disease_scores(collected_data, db)
    candidates = prune_by_required(candidates)
    candidates = apply_differential_rules(candidates, collected_data, db)

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

    return {
        "consultation_id": session_id,
        "message": "直接生成推荐",
        "result": result,
    }


@router.post("/{consultation_id}/answer")
def answer_question(consultation_id: str, req: AnswerRequest, db: Session = Depends(get_db)):
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
def create_registration(req: RegistrationRequest, db: Session = Depends(get_db)):
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

    if req.time_slot not in ("上午", "下午", "晚上"):
        raise HTTPException(status_code=400, detail="时段必须是上午/下午/晚上")

    registration = Registration(
        patient_id=session.patient_id or "anonymous",
        consultation_id=req.consultation_id,
        department_id=req.department_id,
        doctor_id=req.doctor_id,
        registration_date=reg_date,
        time_slot=TimeSlot(req.time_slot),
        status=RegistrationStatus.BOOKED,
    )
    db.add(registration)
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
