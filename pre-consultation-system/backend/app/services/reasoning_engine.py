from typing import Any
from sqlalchemy.orm import Session

from app.models.disease import Disease
from app.models.symptom_dict import SymptomDict
from app.models.symptom_disease import SymptomDisease
from app.models.department import Department
from app.models.differential_rule import DifferentialRule


def calculate_disease_scores(collected_data: dict, db: Session) -> list[dict]:
    """
    根据已收集的症状，计算每个候选疾病的得分。
    score = 匹配症状权重之和 / 该疾病所有症状总权重
    """
    symptom_answers = collected_data.get("symptoms", {})
    matched_symptom_names = {name for name, ans in symptom_answers.items() if ans is True}

    diseases = db.query(Disease).all()
    candidates = []

    for disease in diseases:
        associations = (
            db.query(SymptomDisease)
            .join(SymptomDict, SymptomDisease.symptom_id == SymptomDict.id)
            .filter(SymptomDisease.disease_id == disease.id)
            .all()
        )

        total_weight = sum(a.weight for a in associations) or 1.0
        matched_weight = 0.0
        required_unmet = []

        for assoc in associations:
            sym = db.query(SymptomDict).filter(SymptomDict.id == assoc.symptom_id).first()
            if not sym:
                continue
            if sym.name in matched_symptom_names:
                matched_weight += assoc.weight
            if assoc.is_required and sym.name in symptom_answers and symptom_answers[sym.name] is False:
                required_unmet.append(sym.name)

        dep = db.query(Department).filter(Department.id == disease.department_id).first()
        candidates.append({
            "disease_id": disease.id,
            "disease_name": disease.name,
            "department_id": disease.department_id,
            "department_name": dep.name if dep else "",
            "urgency": disease.urgency.value,
            "score": round(matched_weight / total_weight, 4),
            "matched_weight": matched_weight,
            "total_weight": total_weight,
            "required_met": len(required_unmet) == 0,
            "required_unmet": required_unmet,
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


def prune_by_required(candidates: list[dict]) -> list[dict]:
    """
    排除必要条件不满足的疾病（必要条件症状被回答NO）。
    """
    return [c for c in candidates if c["required_met"] or c["score"] > 0]


def apply_differential_rules(candidates: list[dict], collected_data: dict, db: Session) -> list[dict]:
    """
    应用鉴别诊断规则，调整疾病得分。
    """
    rules = db.query(DifferentialRule).order_by(DifferentialRule.priority).all()
    symptom_answers = collected_data.get("symptoms", {})
    severity = collected_data.get("severity")
    onset_days = collected_data.get("onset_days")

    for rule in rules:
        cond = rule.condition_json
        matched = True

        if "symptoms" in cond:
            required_symptoms = cond["symptoms"]
            for s in required_symptoms:
                if s not in symptom_answers or symptom_answers[s] is not True:
                    matched = False
                    break

        if matched and "onset_days_lt" in cond:
            if onset_days is None or onset_days >= cond["onset_days_lt"]:
                matched = False

        if matched and "severity_gte" in cond:
            if severity is None or severity < cond["severity_gte"]:
                matched = False

        if matched and "severity_lt" in cond:
            if severity is None or severity >= cond["severity_lt"]:
                matched = False

        if matched:
            adjust = rule.result_json.get("disease_adjust", {})
            for candidate in candidates:
                disease_name = candidate["disease_name"]
                if disease_name in adjust:
                    candidate["score"] = round(candidate["score"] + adjust[disease_name], 4)
                    candidate["score"] = max(0.0, min(1.0, candidate["score"]))

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


def select_next_symptom(candidates: list[dict], asked_symptoms: list[str], db: Session) -> dict | None:
    """
    选择鉴别力最高的下一个追问症状。
    优先必要条件，其次按症状在候选疾病中的权重差异度选择。
    """
    asked_set = set(asked_symptoms)
    candidate_symptom_scores: dict[str, dict] = {}

    for candidate in candidates[:10]:
        disease = db.query(Disease).filter(Disease.id == candidate["disease_id"]).first()
        if not disease:
            continue
        associations = (
            db.query(SymptomDisease)
            .join(SymptomDict, SymptomDisease.symptom_id == SymptomDict.id)
            .filter(SymptomDisease.disease_id == disease.id)
            .all()
        )
        for assoc in associations:
            sym = db.query(SymptomDict).filter(SymptomDict.id == assoc.symptom_id).first()
            if not sym or sym.name in asked_set:
                continue
            if sym.name not in candidate_symptom_scores:
                candidate_symptom_scores[sym.name] = {
                    "symptom_id": sym.id,
                    "symptom_name": sym.name,
                    "is_required": assoc.is_required,
                    "weights": [],
                    "max_diff": 0.0,
                }
            candidate_symptom_scores[sym.name]["weights"].append(assoc.weight)

    if not candidate_symptom_scores:
        return None

    for sym_name, info in candidate_symptom_scores.items():
        weights = info["weights"]
        if len(weights) >= 2:
            info["max_diff"] = max(weights) - min(weights)
        else:
            info["max_diff"] = weights[0] if weights else 0

    required_symptoms = {n: i for n, i in candidate_symptom_scores.items() if i["is_required"]}
    if required_symptoms:
        best = max(required_symptoms.values(), key=lambda x: x["max_diff"])
        return {"symptom_id": best["symptom_id"], "symptom_name": best["symptom_name"]}

    non_required = list(candidate_symptom_scores.values())
    if not non_required:
        return None
    best = max(non_required, key=lambda x: x["max_diff"])
    return {"symptom_id": best["symptom_id"], "symptom_name": best["symptom_name"]}


def generate_recommendation(candidates: list[dict], collected_data: dict) -> dict:
    """
    生成科室推荐结果。
    按疾病得分 → 科室聚合 → 生成推荐理由和紧急程度。
    """
    effective = [c for c in candidates if c["score"] > 0]
    effective.sort(key=lambda c: c["score"], reverse=True)

    department_groups: dict[int, dict] = {}
    for c in effective:
        dep_id = c["department_id"]
        if dep_id not in department_groups:
            department_groups[dep_id] = {
                "department_name": c["department_name"],
                "total_score": 0.0,
                "diseases": [],
                "max_urgency": c["urgency"],
                "reasons": [],
            }
        g = department_groups[dep_id]
        g["total_score"] += c["score"]
        g["diseases"].append(c["disease_name"])
        urgency_order = {"紧急": 3, "就诊": 2, "观察": 1}
        if urgency_order.get(c["urgency"], 0) > urgency_order.get(g["max_urgency"], 0):
            g["max_urgency"] = c["urgency"]
        g["reasons"].append(f"{c['disease_name']}({c['score']:.0%})")

    ranked = sorted(
        department_groups.values(),
        key=lambda g: (g["total_score"], len(g["diseases"])),
        reverse=True,
    )

    recommendations = []
    for i, g in enumerate(ranked, start=1):
        urgency_map = {"紧急": "建议立即就医", "就诊": "建议近期就诊", "观察": "可观察等待"}
        recommendations.append({
            "department": g["department_name"],
            "rank": i,
            "reason": "；".join(g["reasons"]),
            "diseases_considered": g["diseases"],
            "urgency": urgency_map.get(g["max_urgency"], "建议就诊"),
        })

    warnings = []
    if collected_data.get("allergies"):
        warnings.extend(f"{a}过敏" for a in collected_data["allergies"])
    if collected_data.get("current_medications"):
        warnings.extend(f"正在服用{m}" for m in collected_data["current_medications"])

    return {
        "recommendations": recommendations,
        "warnings": warnings,
    }
