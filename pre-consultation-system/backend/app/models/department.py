from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Department(Base):
    __tablename__ = "department"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey("department.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text)

    parent = relationship("Department", remote_side="Department.id", backref="children")
