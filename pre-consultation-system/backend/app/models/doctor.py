from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Doctor(Base):
    __tablename__ = "doctor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    title = Column(String(50), nullable=True)
    department_id = Column(Integer, ForeignKey("department.id"), nullable=False)
    introduction = Column(String(500), nullable=True)
    max_patients_per_session = Column(Integer, default=20)

    department = relationship("Department")
