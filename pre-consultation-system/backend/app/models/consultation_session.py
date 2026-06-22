from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone
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
    patient_id = Column(String(50), ForeignKey("user.username", ondelete="SET NULL"), nullable=True)
    status = Column(SAEnum(SessionStatus), nullable=False, default=SessionStatus.INITIAL)
    current_round = Column(Integer, nullable=False, default=0)
    collected_data = Column(JSON, nullable=False)
    candidate_diseases = Column(JSON, nullable=True)
    asked_symptoms = Column(JSON, nullable=True)
    final_recommendation = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    patient = relationship("User", foreign_keys=[patient_id])

    __table_args__ = (
        Index("idx_patient", "patient_id"),
        Index("idx_status", "status"),
    )
