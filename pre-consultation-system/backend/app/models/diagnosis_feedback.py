from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
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

    registration = relationship("Registration", foreign_keys=[registration_id])
    recommended_department = relationship("Department", foreign_keys=[recommended_department_id])
    actual_department = relationship("Department", foreign_keys=[actual_department_id])

    __table_args__ = (
        UniqueConstraint("registration_id", name="uk_registration"),
    )
