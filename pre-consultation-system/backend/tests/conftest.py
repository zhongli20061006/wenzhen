import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.api.auth import create_access_token

from app.models.symptom_dict import SymptomDict, SymptomLevel
from app.models.symptom_synonym import SymptomSynonym
from app.models.disease import Disease, UrgencyLevel
from app.models.symptom_disease import SymptomDisease
from app.models.department import Department
from app.models.differential_rule import DifferentialRule
from app.models.disease_confuser import DiseaseConfuser
from app.models.user import User
from app.models.doctor import Doctor
from app.models.consultation_session import ConsultationSession, SessionStatus
from app.models.question_record import QuestionRecord
from app.models.registration import Registration, RegistrationStatus, TimeSlot
from app.models.diagnosis_feedback import DiagnosisFeedback


###############################################################################
# db_session — 与原始种子数据完全一致，兼容已有 test_reasoning_engine.py
###############################################################################
@pytest.fixture
def db_session():
    db_uri = f"sqlite:///file:test_{uuid.uuid4().hex[:12]}?mode=memory&cache=shared&uri=true"
    engine = create_engine(db_uri, echo=False, connect_args={"check_same_thread": False})
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
        SymptomDisease(symptom_id=1, disease_id=1, weight=1.0, is_required=True),
        SymptomDisease(symptom_id=2, disease_id=2, weight=0.9, is_required=True),
        SymptomDisease(symptom_id=1, disease_id=2, weight=0.9, is_required=True),
        SymptomDisease(symptom_id=3, disease_id=2, weight=0.8, is_required=False),
        SymptomDisease(symptom_id=5, disease_id=2, weight=0.9, is_required=True),
        SymptomDisease(symptom_id=4, disease_id=3, weight=0.8, is_required=False),
        SymptomDisease(symptom_id=2, disease_id=3, weight=0.6, is_required=False),
    ]
    session.add_all(assocs)
    session.flush()

    rule = DifferentialRule(
        id=1, name="发热+头痛+呕吐 → 脑膜炎",
        condition_json={"symptoms": ["发热", "头痛", "呕吐"]},
        result_json={"disease_adjust": {"脑膜炎": 0.3, "普通感冒": -0.1}},
        priority=10,
    )
    session.add(rule)
    session.commit()

    yield session
    session.close()


###############################################################################
# full_db_session — 集成测试完整数据（含用户/医生/会话/挂号/反馈）
###############################################################################
@pytest.fixture
def full_db_session():
    db_uri = f"sqlite:///file:test_{uuid.uuid4().hex[:12]}?mode=memory&cache=shared&uri=true"
    engine = create_engine(db_uri, echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    # 科室
    dep1 = Department(id=1, name="神经内科")
    dep2 = Department(id=2, name="呼吸内科")
    session.add_all([dep1, dep2])
    session.flush()

    # 症状
    s1 = SymptomDict(id=1, name="头痛", category="头颈部", level=SymptomLevel.MAIN)
    s2 = SymptomDict(id=2, name="发热", category="全身", level=SymptomLevel.MAIN)
    s3 = SymptomDict(id=3, name="呕吐", category="消化系统", level=SymptomLevel.SECONDARY)
    s4 = SymptomDict(id=4, name="咳嗽", category="呼吸系统", level=SymptomLevel.MAIN)
    s5 = SymptomDict(id=5, name="颈部僵硬", category="运动系统", level=SymptomLevel.SECONDARY)
    s6 = SymptomDict(id=6, name="流鼻涕", category="呼吸系统", level=SymptomLevel.SECONDARY)
    s7 = SymptomDict(id=7, name="喉咙痛", category="头颈部", level=SymptomLevel.SECONDARY)
    s8 = SymptomDict(id=8, name="肌肉酸痛", category="全身", level=SymptomLevel.SECONDARY)
    session.add_all([s1, s2, s3, s4, s5, s6, s7, s8])
    session.flush()

    # 同义词
    session.add_all([
        SymptomSynonym(id=1, symptom_id=1, term="脑袋疼", weight=1.0),
        SymptomSynonym(id=2, symptom_id=2, term="发烧", weight=1.0),
        SymptomSynonym(id=3, symptom_id=4, term="咳", weight=0.9),
    ])
    session.flush()

    # 疾病
    d1 = Disease(id=1, name="偏头痛", icd_code="G43", department_id=1, urgency=UrgencyLevel.CONSULT)
    d2 = Disease(id=2, name="脑膜炎", icd_code="G03", department_id=1, urgency=UrgencyLevel.EMERGENCY)
    d3 = Disease(id=3, name="普通感冒", icd_code="J00", department_id=2, urgency=UrgencyLevel.CONSULT)
    d4 = Disease(id=4, name="流感", icd_code="J11", department_id=2, urgency=UrgencyLevel.CONSULT)
    session.add_all([d1, d2, d3, d4])
    session.flush()

    # 症状-疾病关联
    assocs = [
        SymptomDisease(symptom_id=1, disease_id=1, weight=1.0, is_required=True, is_discriminative=True),
        SymptomDisease(symptom_id=3, disease_id=1, weight=0.5, is_required=False),
        SymptomDisease(symptom_id=2, disease_id=2, weight=0.9, is_required=True),
        SymptomDisease(symptom_id=1, disease_id=2, weight=0.9, is_required=True, is_discriminative=True),
        SymptomDisease(symptom_id=3, disease_id=2, weight=0.8, is_required=False),
        SymptomDisease(symptom_id=5, disease_id=2, weight=0.9, is_required=True, is_discriminative=True),
        SymptomDisease(symptom_id=8, disease_id=2, weight=0.5, is_required=False),
        SymptomDisease(symptom_id=4, disease_id=3, weight=0.8, is_required=False),
        SymptomDisease(symptom_id=6, disease_id=3, weight=0.7, is_required=False),
        SymptomDisease(symptom_id=7, disease_id=3, weight=0.6, is_required=False),
        SymptomDisease(symptom_id=2, disease_id=3, weight=0.6, is_required=False),
        SymptomDisease(symptom_id=2, disease_id=4, weight=0.9, is_required=True, is_discriminative=True),
        SymptomDisease(symptom_id=4, disease_id=4, weight=0.8, is_required=False),
        SymptomDisease(symptom_id=8, disease_id=4, weight=0.7, is_required=False),
        SymptomDisease(symptom_id=7, disease_id=4, weight=0.5, is_required=False),
    ]
    session.add_all(assocs)
    session.flush()

    # 鉴别规则
    session.add_all([
        DifferentialRule(id=1, name="发热+头痛+呕吐→脑膜炎",
                         condition_json={"symptoms": ["发热", "头痛", "呕吐"]},
                         result_json={"disease_adjust": {"脑膜炎": 0.3, "普通感冒": -0.1, "偏头痛": -0.2}},
                         priority=10),
        DifferentialRule(id=2, name="发热+咳嗽+肌肉酸痛→流感",
                         condition_json={"symptoms": ["发热", "咳嗽", "肌肉酸痛"]},
                         result_json={"disease_adjust": {"流感": 0.2, "普通感冒": -0.1}},
                         priority=5),
    ])
    session.flush()

    # 疾病混淆表
    session.add_all([
        DiseaseConfuser(id=1, disease_a_id=2, disease_b_id=1, distinguishing_symptom_ids=[2, 5]),
        DiseaseConfuser(id=2, disease_a_id=3, disease_b_id=4, distinguishing_symptom_ids=[8]),
    ])
    session.flush()

    # 医生
    session.add_all([
        Doctor(id=1, name="张医生", title="主任医师", department_id=1, max_patients_per_session=20),
        Doctor(id=2, name="李医生", title="副主任医师", department_id=2, max_patients_per_session=25),
    ])
    session.flush()

    # 用户
    import bcrypt
    session.add_all([
        User(id=1, username="patient1", password=bcrypt.hashpw("patient123".encode(), bcrypt.gensalt()).decode(), role="patient"),
        User(id=2, username="doctor_neuro", password=bcrypt.hashpw("doc123".encode(), bcrypt.gensalt()).decode(), role="doctor", doctor_id=1),
        User(id=3, username="admin", password=bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(), role="admin"),
        User(id=4, username="patient2", password=bcrypt.hashpw("patient456".encode(), bcrypt.gensalt()).decode(), role="patient"),
    ])
    session.flush()

    # 问诊会话
    session.add(ConsultationSession(
        id="test-session-001", patient_id="patient1", status=SessionStatus.QUESTIONING, current_round=1,
        collected_data={"symptoms": {"头痛": True, "发热": True}, "onset_days": 2},
        candidate_diseases=[{"disease_id": 2, "disease_name": "脑膜炎", "score": 0.85}],
        asked_symptoms=["头痛", "发热"],
    ))
    session.flush()
    session.add(QuestionRecord(id=1, consultation_id="test-session-001", round=1, symptom_id=1,
                               question_text="您是否有「头痛」的症状？"))
    session.flush()

    # 挂号 + 反馈
    from datetime import date, timedelta
    session.add(Registration(id=1, patient_id="patient1", consultation_id="test-session-001",
                             department_id=1, doctor_id=1, registration_date=date.today(),
                             time_slot=TimeSlot.S0900, status=RegistrationStatus.WAITING))
    session.add(Registration(id=2, patient_id="patient2", consultation_id=None,
                             department_id=1, doctor_id=1,
                             registration_date=date.today() - timedelta(days=1),
                             time_slot=TimeSlot.S0830, status=RegistrationStatus.VISITED))
    session.flush()
    session.add(DiagnosisFeedback(id=1, registration_id=2, consultation_id=None,
                                  recommended_department_id=1, actual_department_id=1,
                                  is_correct=True, doctor_note="诊断正确"))
    session.flush()
    session.commit()
    yield session
    session.close()


###############################################################################
# FastAPI TestClient 夹具
###############################################################################
@pytest.fixture
def client(full_db_session):
    def override_get_db():
        yield full_db_session
    app.dependency_overrides[get_db] = override_get_db
    # Prevent lifespan from connecting to MySQL — redirect engine to SQLite
    import app.main as main_module
    import unittest.mock as _mock
    sqlite_engine = full_db_session.get_bind()
    with _mock.patch.object(main_module, "engine", sqlite_engine):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# ── JWT 认证夹具 ──
@pytest.fixture
def patient_token():
    return create_access_token({"sub": "patient1", "role": "patient", "doctor_id": None})

@pytest.fixture
def patient_headers(patient_token):
    return {"Authorization": f"Bearer {patient_token}"}

@pytest.fixture
def doctor_token():
    return create_access_token({"sub": "doctor_neuro", "role": "doctor", "doctor_id": 1})

@pytest.fixture
def doctor_headers(doctor_token):
    return {"Authorization": f"Bearer {doctor_token}"}

@pytest.fixture
def admin_token():
    return create_access_token({"sub": "admin", "role": "admin", "doctor_id": None})

@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
