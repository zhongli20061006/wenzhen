from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.auth import get_current_user, require_role
from app.schemas.doctor import FeedbackRequest
from app.models.registration import Registration, RegistrationStatus
from app.models.consultation_session import ConsultationSession, SessionStatus
from app.models.diagnosis_feedback import DiagnosisFeedback
from app.models.question_record import QuestionRecord
from app.models.symptom_dict import SymptomDict

router = APIRouter(dependencies=[Depends(require_role("doctor"))])


@router.get("/today-patients")
def today_patients(
    status: str = Query(default=None),
    time_slot: str = Query(default=None),
    db: Session = Depends(get_db),
):
    today = date.today()
    query = db.query(Registration).filter(Registration.registration_date == today)

    if status:
        query = query.filter(Registration.status == status)
    if time_slot:
        query = query.filter(Registration.time_slot == time_slot)

    registrations = query.order_by(Registration.created_at).all()

    return [
        {
            "registration_id": r.id,
            "patient_id": r.patient_id,
            "time_slot": r.time_slot.value,
            "status": r.status.value,
            "department": r.department.name if r.department else "",
            "doctor": r.doctor.name if r.doctor else "",
        }
        for r in registrations
    ]


@router.get("/patient/{registration_id}/report")
def patient_report(registration_id: int, db: Session = Depends(get_db)):
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="挂号记录不存在")

    consultation = None
    questions = []
    if reg.consultation_id:
        consultation = db.query(ConsultationSession).filter(
            ConsultationSession.id == reg.consultation_id
        ).first()
        if consultation:
            q_records = (
                db.query(QuestionRecord)
                .filter(QuestionRecord.consultation_id == consultation.id)
                .order_by(QuestionRecord.round)
                .all()
            )
            for q in q_records:
                symptom_name = ""
                if q.symptom_id:
                    sym = db.query(SymptomDict).filter(SymptomDict.id == q.symptom_id).first()
                    symptom_name = sym.name if sym else ""
                questions.append({
                    "round": q.round,
                    "symptom": symptom_name,
                    "question": q.question_text,
                    "answer": q.answer.value if q.answer else None,
                })

    feedback = db.query(DiagnosisFeedback).filter(
        DiagnosisFeedback.registration_id == registration_id
    ).first()

    return {
        "registration": {
            "id": reg.id,
            "patient_id": reg.patient_id,
            "department": reg.department.name if reg.department else "",
            "doctor": reg.doctor.name if reg.doctor else "",
            "date": reg.registration_date.isoformat(),
            "time_slot": reg.time_slot.value,
            "status": reg.status.value,
        },
        "consultation": {
            "id": consultation.id if consultation else None,
            "status": consultation.status.value if consultation else None,
            "recommendation": consultation.final_recommendation if consultation else None,
            "collected_data": consultation.collected_data if consultation else None,
        },
        "dialog": questions,
        "feedback": {
            "is_correct": feedback.is_correct if feedback else None,
            "actual_department": feedback.actual_department_id if feedback else None,
            "doctor_note": feedback.doctor_note if feedback else None,
        },
    }


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    reg = db.query(Registration).filter(Registration.id == req.registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="挂号记录不存在")

    existing = db.query(DiagnosisFeedback).filter(
        DiagnosisFeedback.registration_id == req.registration_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该记录已有反馈")

    consultation = db.query(ConsultationSession).filter(
        ConsultationSession.id == reg.consultation_id
    ).first()

    feedback = DiagnosisFeedback(
        registration_id=req.registration_id,
        consultation_id=reg.consultation_id,
        recommended_department_id=reg.department_id,
        actual_department_id=req.actual_department_id,
        is_correct=req.is_correct,
        doctor_note=req.doctor_note,
    )
    db.add(feedback)
    reg.status = RegistrationStatus.VISITED
    if consultation:
        consultation.status = SessionStatus.COMPLETED
    db.commit()

    return {"message": "反馈提交成功"}
