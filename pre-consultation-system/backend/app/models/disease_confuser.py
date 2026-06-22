from sqlalchemy import Column, Integer, JSON, ForeignKey
from app.database import Base


class DiseaseConfuser(Base):
    __tablename__ = "disease_confuser"

    id = Column(Integer, primary_key=True, autoincrement=True)
    disease_a_id = Column(Integer, ForeignKey("disease.id", ondelete="CASCADE"), nullable=False, index=True)
    disease_b_id = Column(Integer, ForeignKey("disease.id", ondelete="CASCADE"), nullable=False, index=True)
    distinguishing_symptom_ids = Column(JSON, nullable=False, comment="区分两种疾病的症状ID列表")
