from sqlalchemy import Column, Integer, String, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UrgencyLevel(str, enum.Enum):
    EMERGENCY = "紧急"
    CONSULT = "就诊"
    OBSERVE = "观察"


class Disease(Base):
    __tablename__ = "disease"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    icd_code = Column(String(20), unique=True, nullable=True)
    description = Column(Text)
    urgency = Column(SAEnum(UrgencyLevel), default=UrgencyLevel.CONSULT)
    department_id = Column(Integer, ForeignKey("department.id", ondelete="SET NULL"), nullable=True)

    department = relationship("Department")
