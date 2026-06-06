from sqlalchemy import Column, Integer, String, Date, DateTime, Enum as SAEnum, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


class TimeSlot(str, enum.Enum):
    MORNING = "上午"
    AFTERNOON = "下午"
    EVENING = "晚上"


class RegistrationStatus(str, enum.Enum):
    BOOKED = "已预约"
    WAITING = "等待中"
    VISITED = "已就诊"
    MISSED = "已过号"
    CANCELLED = "已取消"


class Registration(Base):
    __tablename__ = "registration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(20), nullable=False)
    consultation_id = Column(String(36), ForeignKey("consultation_session.id", ondelete="SET NULL"), nullable=True)
    department_id = Column(Integer, ForeignKey("department.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctor.id"), nullable=True)
    registration_date = Column(Date, nullable=False)
    time_slot = Column(SAEnum(TimeSlot), nullable=False)
    status = Column(SAEnum(RegistrationStatus), nullable=False, default=RegistrationStatus.BOOKED)
    created_at = Column(DateTime, default=datetime.now)

    department = relationship("Department")
    doctor = relationship("Doctor")

    __table_args__ = (
        Index("idx_reg_patient", "patient_id"),
        Index("idx_doctor_date", "doctor_id", "registration_date"),
    )
