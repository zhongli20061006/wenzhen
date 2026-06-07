from app.models.symptom_dict import SymptomDict
from app.models.department import Department
from app.models.disease import Disease
from app.models.symptom_disease import SymptomDisease
from app.models.differential_rule import DifferentialRule
from app.models.consultation_session import ConsultationSession
from app.models.question_record import QuestionRecord
from app.models.doctor import Doctor
from app.models.registration import Registration
from app.models.diagnosis_feedback import DiagnosisFeedback
from app.models.user import User
from app.models.symptom_synonym import SymptomSynonym
from app.models.disease_confuser import DiseaseConfuser

__all__ = [
    "SymptomDict",
    "Department",
    "Disease",
    "SymptomDisease",
    "DifferentialRule",
    "ConsultationSession",
    "QuestionRecord",
    "Doctor",
    "Registration",
    "DiagnosisFeedback",
    "User",
    "SymptomSynonym",
    "DiseaseConfuser",
]
