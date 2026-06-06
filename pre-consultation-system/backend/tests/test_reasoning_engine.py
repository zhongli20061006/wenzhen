# -*- coding: utf-8 -*-
import pytest
from app.services.reasoning_engine import (
    calculate_disease_scores,
    prune_by_required,
    apply_differential_rules,
    select_next_symptom,
    generate_recommendation,
)


class TestCalculateDiseaseScores:
    def test_all_symptoms_matched(self, db_session):
        data = {"symptoms": {"头痛": True, "发热": True, "咳嗽": True}}
        candidates = calculate_disease_scores(data, db_session)
        scores = {c["disease_name"]: c["score"] for c in candidates}
        assert scores["偏头痛"] == 1.0
        assert scores["脑膜炎"] == pytest.approx(1.8 / 3.5, 2)
        assert scores["普通感冒"] == 1.0

    def test_partial_match(self, db_session):
        data = {"symptoms": {"头痛": True}}
        candidates = calculate_disease_scores(data, db_session)
        scores = {c["disease_name"]: c["score"] for c in candidates}
        assert scores["偏头痛"] == 1.0
        assert scores["脑膜炎"] == pytest.approx(0.9 / 3.5, 2)

    def test_no_match(self, db_session):
        data = {"symptoms": {}}
        candidates = calculate_disease_scores(data, db_session)
        for c in candidates:
            assert c["score"] == 0.0


class TestPruneByRequired:
    def test_required_met(self):
        candidates = [
            {"disease_name": "脑膜炎", "required_met": True, "score": 0.8},
            {"disease_name": "偏头痛", "required_met": False, "score": 0.0},
        ]
        result = prune_by_required(candidates)
        names = [c["disease_name"] for c in result]
        assert "脑膜炎" in names
        assert "偏头痛" not in names

    def test_score_keeps_partial(self):
        candidates = [
            {"disease_name": "偏头痛", "required_met": False, "score": 0.5},
        ]
        result = prune_by_required(candidates)
        assert len(result) == 1


class TestDifferentialRules:
    def test_rule_applies(self, db_session):
        data = {"symptoms": {"发热": True, "头痛": True, "呕吐": True}}
        candidates = [
            {"disease_name": "脑膜炎", "score": 0.5, "department_id": 1, "department_name": "神经内科",
             "urgency": "紧急", "disease_id": 2, "matched_weight": 0, "total_weight": 1,
             "required_met": True, "required_unmet": []},
            {"disease_name": "普通感冒", "score": 0.4, "department_id": 2, "department_name": "呼吸内科",
             "urgency": "就诊", "disease_id": 3, "matched_weight": 0, "total_weight": 1,
             "required_met": True, "required_unmet": []},
        ]
        result = apply_differential_rules(candidates, data, db_session)
        scores = {c["disease_name"]: c["score"] for c in result}
        assert scores["脑膜炎"] == pytest.approx(0.8, 2)
        assert scores["普通感冒"] == pytest.approx(0.3, 2)

    def test_rule_not_applies(self, db_session):
        data = {"symptoms": {"发热": True}}
        candidates = [
            {"disease_name": "脑膜炎", "score": 0.5, "department_id": 1, "department_name": "神经内科",
             "urgency": "紧急", "disease_id": 2, "matched_weight": 0, "total_weight": 1,
             "required_met": True, "required_unmet": []},
            {"disease_name": "普通感冒", "score": 0.4, "department_id": 2, "department_name": "呼吸内科",
             "urgency": "就诊", "disease_id": 3, "matched_weight": 0, "total_weight": 1,
             "required_met": True, "required_unmet": []},
        ]
        result = apply_differential_rules(candidates, data, db_session)
        assert result == candidates


class TestSelectNextSymptom:
    def test_select_required_symptom(self, db_session):
        candidates = [
            {"disease_id": 2, "disease_name": "脑膜炎", "score": 0.8},
        ]
        result = select_next_symptom(candidates, ["头痛", "发热"], db_session)
        assert result is not None
        assert result["symptom_name"] == "颈部僵硬"

    def test_no_candidates(self, db_session):
        result = select_next_symptom([], ["头痛"], db_session)
        assert result is None

    def test_all_asked(self, db_session):
        candidates = [
            {"disease_id": 2, "disease_name": "脑膜炎", "score": 0.8},
        ]
        result = select_next_symptom(candidates, ["头痛", "发热", "呕吐", "颈部僵硬"], db_session)
        assert result is None


class TestGenerateRecommendation:
    def test_valid_recommendation(self):
        candidates = [
            {"score": 0.9, "department_id": 1, "department_name": "神经内科",
             "disease_name": "脑膜炎", "urgency": "紧急", "disease_id": 2,
             "matched_weight": 0, "total_weight": 1, "required_met": True, "required_unmet": []},
            {"score": 0.3, "department_id": 2, "department_name": "呼吸内科",
             "disease_name": "普通感冒", "urgency": "就诊", "disease_id": 3,
             "matched_weight": 0, "total_weight": 1, "required_met": True, "required_unmet": []},
        ]
        collected = {"allergies": ["青霉素"], "current_medications": []}
        result = generate_recommendation(candidates, collected)
        assert len(result["recommendations"]) == 2
        assert result["recommendations"][0]["department"] == "神经内科"
        assert result["recommendations"][0]["rank"] == 1
        assert "青霉素过敏" in result["warnings"]

    def test_empty_candidates(self):
        result = generate_recommendation([], {})
        assert result["recommendations"] == []
