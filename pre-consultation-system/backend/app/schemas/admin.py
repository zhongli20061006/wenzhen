from pydantic import BaseModel
from typing import Optional


class SymptomCreate(BaseModel):
    name: str
    aliases: Optional[str] = None
    category: Optional[str] = None
    level: str = "次要"


class DiseaseCreate(BaseModel):
    name: str
    icd_code: Optional[str] = None
    description: Optional[str] = None
    urgency: str = "就诊"
    department_id: Optional[int] = None


class DepartmentCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None


class SymptomDiseaseCreate(BaseModel):
    symptom_id: int
    disease_id: int
    weight: float = 1.0
    is_required: bool = False


class DifferentialRuleCreate(BaseModel):
    name: str
    condition_json: dict
    result_json: dict
    priority: int = 1
    description: Optional[str] = None
