from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, ForeignKey, UniqueConstraint
from app.database import Base
from datetime import datetime
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
    symptom_id = Column(Integer, nullable=True)
    question_text = Column(String(500), nullable=False)
    answer = Column(SAEnum(AnswerType), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("consultation_id", "round", name="uk_round"),
    )
