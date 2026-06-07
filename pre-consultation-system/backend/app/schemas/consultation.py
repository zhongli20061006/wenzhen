from pydantic import BaseModel
from typing import Optional


class StartConsultationRequest(BaseModel):
    symptoms: list[str]
    onset_date: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[int] = None
    medical_history: Optional[list[str]] = None
    current_medications: Optional[list[str]] = None
    allergies: Optional[list[str]] = None


class AnswerRequest(BaseModel):
    symptom_id: int
    answer: str


class QuestionResponse(BaseModel):
    question_id: int
    question_text: str
    symptom_id: int
    round: int
    total_rounds: int


class RecommendItem(BaseModel):
    department: str
    rank: int
    reason: str
    diseases_considered: list[str]
    urgency: str


class RecommendResult(BaseModel):
    recommendations: list[RecommendItem]
    warnings: list[str]


class RegistrationRequest(BaseModel):
    consultation_id: Optional[str] = None
    department_id: int
    doctor_id: int
    registration_date: str
    time_slot: str
