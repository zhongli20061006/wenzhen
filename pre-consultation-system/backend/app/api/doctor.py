from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer

from app.database import get_db
from app.api.auth import get_current_user, require_role
from app.logger import logger
from app.schemas.doctor import FeedbackRequest
from app.models.registration import Registration, RegistrationStatus, TimeSlot
from app.models.consultation_session import ConsultationSession, SessionStatus
from app.models.diagnosis_feedback import DiagnosisFeedback
from app.models.question_record import QuestionRecord
from app.models.symptom_dict import SymptomDict

router = APIRouter(dependencies=[Depends(require_role("doctor"))])


@router.get("/today-patients")
def today_patients(
    current_user: dict = Depends(get_current_user),
    status: str = Query(default="等待中"),
    period: str = Query(default=None),
    time_slot: str = Query(default=None),
    db: Session = Depends(get_db),
):
    today = date.today()
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=403, detail="当前用户未关联医生信息")
    query = db.query(Registration).filter(
        Registration.registration_date == today,
        Registration.doctor_id == doctor_id,
    )

    if status:
        query = query.filter(Registration.status == status)
    if time_slot:
        query = query.filter(Registration.time_slot == time_slot)

    registrations = query.order_by(Registration.created_at).all()

    if period:
        registrations = [r for r in registrations if TimeSlot.period(r.time_slot) == period]

    return [
        {
            "registration_id": r.id,
            "patient_id": r.patient_id,
            "time_slot": r.time_slot.value,
            "period": TimeSlot.period(r.time_slot),
            "status": r.status.value,
            "department": r.department.name if r.department else "",
            "doctor": r.doctor.name if r.doctor else "",
            "date": r.registration_date.isoformat(),
        }
        for r in registrations
    ]


@router.get("/patient/{registration_id}/report")
def patient_report(
    registration_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="挂号记录不存在")

    # 医生只能查看分配给自己的患者报告
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=403, detail="当前用户未关联医生信息")
    if reg.doctor_id != doctor_id:
        raise HTTPException(status_code=403, detail="无权查看其他医生的患者报告")

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
            # 批量查询症状名，避免 N+1
            symptom_ids = [q.symptom_id for q in q_records if q.symptom_id]
            symptom_map = {}
            if symptom_ids:
                for s in db.query(SymptomDict).filter(SymptomDict.id.in_(symptom_ids)).all():
                    symptom_map[s.id] = s.name
            for q in q_records:
                symptom_name = symptom_map.get(q.symptom_id, "")
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
            "department_id": reg.department_id,
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
def submit_feedback(
    req: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reg = db.query(Registration).filter(Registration.id == req.registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="挂号记录不存在")

    # 医生只能对自己接诊的患者提交反馈
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=403, detail="当前用户未关联医生信息")
    if reg.doctor_id != doctor_id:
        raise HTTPException(status_code=403, detail="无权对其他医生的患者提交反馈")

    existing = db.query(DiagnosisFeedback).filter(
        DiagnosisFeedback.registration_id == req.registration_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该记录已有反馈")

    consultation = db.query(ConsultationSession).filter(
        ConsultationSession.id == reg.consultation_id
    ).first()

    logger.info("医生提交反馈 registration_id=%d, is_correct=%s, error_reason=%s", req.registration_id, req.is_correct, req.error_reason)
    feedback = DiagnosisFeedback(
        registration_id=req.registration_id,
        consultation_id=reg.consultation_id,
        recommended_department_id=reg.department_id,
        actual_department_id=req.actual_department_id,
        is_correct=req.is_correct,
        error_reason=req.error_reason,
        doctor_note=req.doctor_note,
    )
    db.add(feedback)
    reg.status = RegistrationStatus.VISITED
    if consultation:
        consultation.status = SessionStatus.COMPLETED
    db.commit()

    return {"message": "反馈提交成功"}


@router.get("/feedback-history")
def feedback_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=403, detail="当前用户未关联医生信息")
    query = (
        db.query(DiagnosisFeedback)
        .join(Registration, DiagnosisFeedback.registration_id == Registration.id)
        .filter(Registration.doctor_id == doctor_id)
    )
    feedbacks = query.order_by(DiagnosisFeedback.id.desc()).limit(50).all()
    return [
        {
            "id": f.id,
            "registration_id": f.registration_id,
            "is_correct": f.is_correct,
            "error_reason": f.error_reason,
            "doctor_note": f.doctor_note,
            "recommended_dept": f.recommended_department.name if f.recommended_department else "",
            "actual_dept": f.actual_department.name if f.actual_department else "",
            "patient_id": f.registration.patient_id if f.registration else "",
            "date": f.registration.registration_date.isoformat() if f.registration else "",
        }
        for f in feedbacks
    ]


@router.get("/accuracy")
def doctor_accuracy(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=403, detail="当前用户未关联医生信息")
    query = db.query(DiagnosisFeedback).join(
        Registration, DiagnosisFeedback.registration_id == Registration.id
    ).filter(Registration.doctor_id == doctor_id)

    total = query.count()
    correct = query.filter(DiagnosisFeedback.is_correct == True).count()
    incorrect = total - correct
    accuracy = round(correct / total, 4) if total > 0 else 0

    # Per-department breakdown
    from app.models.department import Department
    dept_q = (
        db.query(
            DiagnosisFeedback.recommended_department_id,
            func.count().label("total"),
            func.sum(DiagnosisFeedback.is_correct.cast(Integer)).label("correct"),
        )
        .join(Registration, DiagnosisFeedback.registration_id == Registration.id)
        .filter(Registration.doctor_id == doctor_id)
    )
    dept_stats = dept_q.group_by(DiagnosisFeedback.recommended_department_id).all()

    by_dept = []
    # 批量查询科室名，避免 N+1
    dept_ids = [row.recommended_department_id for row in dept_stats if row.recommended_department_id]
    dept_map = {}
    if dept_ids:
        for d in db.query(Department).filter(Department.id.in_(dept_ids)).all():
            dept_map[d.id] = d.name
    for row in dept_stats:
        t = row.total
        c = row.correct or 0
        by_dept.append({
            "department_id": row.recommended_department_id,
            "department_name": dept_map.get(row.recommended_department_id, ""),
            "total": t,
            "correct": c,
            "accuracy": round(c / t, 4) if t > 0 else 0,
        })

    # Error reason breakdown (scoped to this doctor)
    error_stats = (
        db.query(
            DiagnosisFeedback.error_reason,
            func.count().label("cnt"),
        )
        .join(Registration, DiagnosisFeedback.registration_id == Registration.id)
        .filter(DiagnosisFeedback.is_correct == False)
        .filter(Registration.doctor_id == doctor_id)
    )
    error_stats = error_stats.group_by(DiagnosisFeedback.error_reason).all()
    error_breakdown = {row.error_reason or "未填写": row.cnt for row in error_stats}

    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": accuracy,
        "by_department": by_dept,
        "error_reasons": error_breakdown,
    }
