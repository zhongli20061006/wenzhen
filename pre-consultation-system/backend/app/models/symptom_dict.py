from sqlalchemy import Column, Integer, String, Enum as SAEnum
from app.database import Base
import enum


class SymptomLevel(str, enum.Enum):
    MAIN = "主要"
    SECONDARY = "次要"


class SymptomDict(Base):
    __tablename__ = "symptom_dict"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    aliases = Column(String(255), comment="别名，逗号分隔")
    category = Column(String(50), comment="全身、头颈部、消化系统等")
    level = Column(SAEnum(SymptomLevel), default=SymptomLevel.SECONDARY)
