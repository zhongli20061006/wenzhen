from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from app.database import Base
from datetime import datetime


class DiagnosisFeedback(Base):
    __tablename__ = "diagnosis_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    registration_id = Column(Integer, ForeignKey("registration.id"), nullable=False)
    consultation_id = Column(String(36), ForeignKey("consultation_session.id", ondelete="SET NULL"), nullable=True)
    recommended_department_id = Column(Integer, ForeignKey("department.id"), nullable=True)
    actual_department_id = Column(Integer, ForeignKey("department.id"), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    doctor_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("registration_id", name="uk_registration"),
    )
