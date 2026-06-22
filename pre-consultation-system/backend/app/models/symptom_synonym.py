from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base


class SymptomSynonym(Base):
    __tablename__ = "symptom_synonym"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symptom_id = Column(Integer, ForeignKey("symptom_dict.id", ondelete="CASCADE"), nullable=False, index=True)
    term = Column(String(100), nullable=False, comment="同义词/口语化表达")
    weight = Column(Float, default=1.0, comment="匹配权重0.0-1.0")
