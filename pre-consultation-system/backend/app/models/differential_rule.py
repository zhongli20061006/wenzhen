from sqlalchemy import Column, Integer, String, Text, JSON
from app.database import Base


class DifferentialRule(Base):
    __tablename__ = "differential_rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    condition_json = Column(JSON, nullable=False, comment="触发条件")
    result_json = Column(JSON, nullable=False, comment="结论")
    priority = Column(Integer, default=1)
    description = Column(Text)
