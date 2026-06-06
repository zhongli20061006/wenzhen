from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.api.auth import get_current_user, require_role
from app.schemas.admin import (
    SymptomCreate,
    DiseaseCreate,
    DepartmentCreate,
    SymptomDiseaseCreate,
    DifferentialRuleCreate,
)
from app.models.symptom_dict import SymptomDict
from app.models.disease import Disease
from app.models.department import Department
from app.models.symptom_disease import SymptomDisease
from app.models.differential_rule import DifferentialRule
from app.models.registration import Registration
from app.models.diagnosis_feedback import DiagnosisFeedback

router = APIRouter(dependencies=[Depends(require_role("admin"))])


@router.get("/symptoms")
def list_symptoms(db: Session = Depends(get_db)):
    return db.query(SymptomDict).all()


@router.post("/symptoms")
def create_symptom(req: SymptomCreate, db: Session = Depends(get_db)):
    existing = db.query(SymptomDict).filter(SymptomDict.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="症状已存在")
    sym = SymptomDict(name=req.name, aliases=req.aliases, category=req.category, level=req.level)
    db.add(sym)
    db.commit()
    return sym


@router.put("/symptoms/{symptom_id}")
def update_symptom(symptom_id: int, req: SymptomCreate, db: Session = Depends(get_db)):
    sym = db.query(SymptomDict).filter(SymptomDict.id == symptom_id).first()
    if not sym:
        raise HTTPException(status_code=404, detail="症状不存在")
    sym.name = req.name
    sym.aliases = req.aliases
    sym.category = req.category
    sym.level = req.level
    db.commit()
    return sym


@router.delete("/symptoms/{symptom_id}")
def delete_symptom(symptom_id: int, db: Session = Depends(get_db)):
    sym = db.query(SymptomDict).filter(SymptomDict.id == symptom_id).first()
    if not sym:
        raise HTTPException(status_code=404, detail="症状不存在")
    db.delete(sym)
    db.commit()
    return {"message": "删除成功"}


@router.get("/diseases")
def list_diseases(db: Session = Depends(get_db)):
    return db.query(Disease).all()


@router.post("/diseases")
def create_disease(req: DiseaseCreate, db: Session = Depends(get_db)):
    existing = db.query(Disease).filter(Disease.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="疾病已存在")
    dis = Disease(
        name=req.name, icd_code=req.icd_code, description=req.description,
        urgency=req.urgency, department_id=req.department_id,
    )
    db.add(dis)
    db.commit()
    return dis


@router.put("/diseases/{disease_id}")
def update_disease(disease_id: int, req: DiseaseCreate, db: Session = Depends(get_db)):
    dis = db.query(Disease).filter(Disease.id == disease_id).first()
    if not dis:
        raise HTTPException(status_code=404, detail="疾病不存在")
    dis.name = req.name
    dis.icd_code = req.icd_code
    dis.description = req.description
    dis.urgency = req.urgency
    dis.department_id = req.department_id
    db.commit()
    return dis


@router.delete("/diseases/{disease_id}")
def delete_disease(disease_id: int, db: Session = Depends(get_db)):
    dis = db.query(Disease).filter(Disease.id == disease_id).first()
    if not dis:
        raise HTTPException(status_code=404, detail="疾病不存在")
    db.delete(dis)
    db.commit()
    return {"message": "删除成功"}


@router.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()


@router.post("/departments")
def create_department(req: DepartmentCreate, db: Session = Depends(get_db)):
    existing = db.query(Department).filter(Department.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="科室已存在")
    dep = Department(name=req.name, parent_id=req.parent_id, description=req.description)
    db.add(dep)
    db.commit()
    return dep


@router.put("/departments/{department_id}")
def update_department(department_id: int, req: DepartmentCreate, db: Session = Depends(get_db)):
    dep = db.query(Department).filter(Department.id == department_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="科室不存在")
    dep.name = req.name
    dep.parent_id = req.parent_id
    dep.description = req.description
    db.commit()
    return dep


@router.delete("/departments/{department_id}")
def delete_department(department_id: int, db: Session = Depends(get_db)):
    dep = db.query(Department).filter(Department.id == department_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="科室不存在")
    db.delete(dep)
    db.commit()
    return {"message": "删除成功"}


@router.get("/symptom-disease")
def list_symptom_disease(db: Session = Depends(get_db)):
    return db.query(SymptomDisease).all()


@router.post("/symptom-disease")
def create_symptom_disease(req: SymptomDiseaseCreate, db: Session = Depends(get_db)):
    existing = db.query(SymptomDisease).filter(
        SymptomDisease.symptom_id == req.symptom_id,
        SymptomDisease.disease_id == req.disease_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="关联已存在")
    sd = SymptomDisease(
        symptom_id=req.symptom_id, disease_id=req.disease_id,
        weight=req.weight, is_required=req.is_required,
    )
    db.add(sd)
    db.commit()
    return sd


@router.delete("/symptom-disease/{sd_id}")
def delete_symptom_disease(sd_id: int, db: Session = Depends(get_db)):
    sd = db.query(SymptomDisease).filter(SymptomDisease.id == sd_id).first()
    if not sd:
        raise HTTPException(status_code=404, detail="关联不存在")
    db.delete(sd)
    db.commit()
    return {"message": "删除成功"}


@router.get("/differential-rules")
def list_rules(db: Session = Depends(get_db)):
    return db.query(DifferentialRule).all()


@router.post("/differential-rules")
def create_rule(req: DifferentialRuleCreate, db: Session = Depends(get_db)):
    existing = db.query(DifferentialRule).filter(DifferentialRule.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="规则已存在")
    rule = DifferentialRule(
        name=req.name, condition_json=req.condition_json,
        result_json=req.result_json, priority=req.priority,
        description=req.description,
    )
    db.add(rule)
    db.commit()
    return rule


@router.put("/differential-rules/{rule_id}")
def update_rule(rule_id: int, req: DifferentialRuleCreate, db: Session = Depends(get_db)):
    rule = db.query(DifferentialRule).filter(DifferentialRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.name = req.name
    rule.condition_json = req.condition_json
    rule.result_json = req.result_json
    rule.priority = req.priority
    rule.description = req.description
    db.commit()
    return rule


@router.delete("/differential-rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(DifferentialRule).filter(DifferentialRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}


@router.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    total_consultations = db.query(Registration).count()
    total_feedback = db.query(DiagnosisFeedback).count()
    correct_feedback = db.query(DiagnosisFeedback).filter(DiagnosisFeedback.is_correct == True).count()
    accuracy = round(correct_feedback / total_feedback, 4) if total_feedback > 0 else 0

    last_week = date.today() - timedelta(days=7)
    weekly = db.query(Registration).filter(Registration.created_at >= last_week).count()

    return {
        "total_consultations": total_consultations,
        "weekly_consultations": weekly,
        "total_feedback": total_feedback,
        "accuracy": accuracy,
        "correct_count": correct_feedback,
        "incorrect_count": total_feedback - correct_feedback,
    }
