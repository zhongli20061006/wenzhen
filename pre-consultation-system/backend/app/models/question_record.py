from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone
import enum


class AnswerType(str, enum.Enum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class QuestionRecord(Base):
    __tablename__ = "question_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(String(36), ForeignKey("consultation_session.id", ondelete="CASCADE"), nullable=False)
    round = Column(Integer, nullable=False)
    symptom_id = Column(Integer, ForeignKey("symptom_dict.id", ondelete="SET NULL"), nullable=True)
    question_text = Column(String(500), nullable=False)
    answer = Column(SAEnum(AnswerType), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("consultation_id", "round", name="uk_round"),
    )
