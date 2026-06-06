import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.symptom_dict import SymptomDict, SymptomLevel
from app.models.disease import Disease, UrgencyLevel
from app.models.symptom_disease import SymptomDisease
from app.models.department import Department
from app.models.differential_rule import DifferentialRule


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    dep = Department(id=1, name="神经内科")
    session.add(dep)
    dep2 = Department(id=2, name="呼吸内科")
    session.add(dep2)
    session.flush()

    s1 = SymptomDict(id=1, name="头痛", category="头颈部", level=SymptomLevel.MAIN)
    s2 = SymptomDict(id=2, name="发热", category="全身", level=SymptomLevel.MAIN)
    s3 = SymptomDict(id=3, name="呕吐", category="消化系统", level=SymptomLevel.SECONDARY)
    s4 = SymptomDict(id=4, name="咳嗽", category="呼吸系统", level=SymptomLevel.MAIN)
    s5 = SymptomDict(id=5, name="颈部僵硬", category="运动系统", level=SymptomLevel.SECONDARY)
    session.add_all([s1, s2, s3, s4, s5])
    session.flush()

    d1 = Disease(id=1, name="偏头痛", icd_code="G43", department_id=1, urgency=UrgencyLevel.CONSULT)
    d2 = Disease(id=2, name="脑膜炎", icd_code="G03", department_id=1, urgency=UrgencyLevel.EMERGENCY)
    d3 = Disease(id=3, name="普通感冒", icd_code="J00", department_id=2, urgency=UrgencyLevel.CONSULT)
    session.add_all([d1, d2, d3])
    session.flush()

    assocs = [
        SymptomDisease(symptom_id=1, disease_id=1, weight=1.0, is_required=True),  # 头痛 → 偏头痛
        SymptomDisease(symptom_id=2, disease_id=2, weight=0.9, is_required=True),  # 发热 → 脑膜炎
        SymptomDisease(symptom_id=1, disease_id=2, weight=0.9, is_required=True),  # 头痛 → 脑膜炎
        SymptomDisease(symptom_id=3, disease_id=2, weight=0.8, is_required=False), # 呕吐 → 脑膜炎
        SymptomDisease(symptom_id=5, disease_id=2, weight=0.9, is_required=True),  # 颈部僵硬 → 脑膜炎
        SymptomDisease(symptom_id=4, disease_id=3, weight=0.8, is_required=False), # 咳嗽 → 感冒
        SymptomDisease(symptom_id=2, disease_id=3, weight=0.6, is_required=False), # 发热 → 感冒
    ]
    session.add_all(assocs)
    session.flush()

    rule = DifferentialRule(
        id=1,
        name="发热+头痛+呕吐 → 脑膜炎",
        condition_json={"symptoms": ["发热", "头痛", "呕吐"]},
        result_json={"disease_adjust": {"脑膜炎": 0.3, "普通感冒": -0.1}},
        priority=10,
    )
    session.add(rule)
    session.commit()

    yield session
    session.close()
