from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, Index
from sqlalchemy.dialects.mysql import JSON
from app.database import Base
from datetime import datetime
import enum


class SessionStatus(str, enum.Enum):
    INITIAL = "INITIAL"
    QUESTIONING = "QUESTIONING"
    RECOMMENDING = "RECOMMENDING"
    BOOKING = "BOOKING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ConsultationSession(Base):
    __tablename__ = "consultation_session"

    id = Column(String(36), primary_key=True)
    patient_id = Column(String(20), nullable=True)
    status = Column(SAEnum(SessionStatus), nullable=False, default=SessionStatus.INITIAL)
    current_round = Column(Integer, nullable=False, default=0)
    collected_data = Column(JSON, nullable=False)
    candidate_diseases = Column(JSON, nullable=True)
    asked_symptoms = Column(JSON, nullable=True)
    final_recommendation = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_patient", "patient_id"),
        Index("idx_status", "status"),
    )
