from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey, UniqueConstraint
from app.database import Base


class SymptomDisease(Base):
    __tablename__ = "symptom_disease"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symptom_id = Column(Integer, ForeignKey("symptom_dict.id", ondelete="CASCADE"), nullable=False)
    disease_id = Column(Integer, ForeignKey("disease.id", ondelete="CASCADE"), nullable=False)
    weight = Column(Float, default=1.0, comment="权重0.0-1.0")
    is_required = Column(Boolean, default=False, comment="是否必要条件")
    is_positive = Column(Boolean, default=True, comment="阳性症状(True)或阴性排除(False)")
    is_discriminative = Column(Boolean, default=False, comment="是否为关键鉴别症状")

    __table_args__ = (
        UniqueConstraint("symptom_id", "disease_id", name="uk_pair"),
    )
