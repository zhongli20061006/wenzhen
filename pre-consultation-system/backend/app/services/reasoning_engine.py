from typing import Any
from sqlalchemy.orm import Session

from app.models.disease import Disease
from app.models.symptom_dict import SymptomDict
from app.models.symptom_disease import SymptomDisease
from app.models.department import Department
from app.models.differential_rule import DifferentialRule
from app.models.disease_confuser import DiseaseConfuser


def calculate_disease_scores(collected_data: dict, db: Session) -> list[dict]:
    """
    根据已收集的症状，计算每个候选疾病的得分。
    score = (positive_matched_weight * 1.0 + negative_met_weight * 0.6) / total_weight
    阳性症状命中加分，阴性症状未被命中扣分，鉴别症状加权 1.5 倍。
    """
    symptom_answers = collected_data.get("symptoms", {})
    matched_symptom_names = {name for name, ans in symptom_answers.items() if ans is True}
    negative_symptom_names = {name for name, ans in symptom_answers.items() if ans is False}

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
        positive_matched = 0.0
        negative_met = 0.0
        required_unmet = []

        for assoc in associations:
            sym = db.query(SymptomDict).filter(SymptomDict.id == assoc.symptom_id).first()
            if not sym:
                continue

            multiplier = 1.5 if assoc.is_discriminative else 1.0

            if assoc.is_positive:
                if sym.name in matched_symptom_names:
                    positive_matched += assoc.weight * multiplier
                if assoc.is_required and sym.name in symptom_answers and symptom_answers[sym.name] is False:
                    required_unmet.append(sym.name)
            else:
                if sym.name in negative_symptom_names:
                    positive_matched += assoc.weight * multiplier * 0.6
                elif sym.name not in matched_symptom_names:
                    negative_met += assoc.weight * multiplier * 0.3

        effective = positive_matched + negative_met
        dep = db.query(Department).filter(Department.id == disease.department_id).first()
        candidates.append({
            "disease_id": disease.id,
            "disease_name": disease.name,
            "department_id": disease.department_id,
            "department_name": dep.name if dep else "",
            "urgency": disease.urgency.value,
            "score": round(effective / total_weight, 4),
            "matched_weight": positive_matched,
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
    基于鉴别力(discriminative power)选择下一个追问症状。

    算法：
    1. 对每个未问症状 s，计算其区分力：
       disc(s) = sum over all disease pairs (d_i, d_j):
         |weight(s, d_i) - weight(s, d_j)| * score(d_i) * score(d_j)
    2. 疾病混淆加分: 若 s 在疾病混淆表中标记为鉴别症状，×1.5
    3. 鉴别标记加分: 若 is_discriminative=True，×1.3
    4. 必要条件优先: 若 is_required=True，×2.0
    5. 阴性症状略降权: 若 is_positive=False，×0.8
    6. 归一化到 0-10 供调试

    返回区分力最高的症状。
    """
    asked_set = set(asked_symptoms)
    top = candidates[:10]
    if not top:
        return None

    top_ids = [c["disease_id"] for c in top]
    score_map = {c["disease_id"]: c["score"] for c in top}

    all_assocs = db.query(SymptomDisease).filter(
        SymptomDisease.disease_id.in_(top_ids)
    ).all()

    symptom_ids = list({a.symptom_id for a in all_assocs})
    symptoms = {s.id: s for s in db.query(SymptomDict).filter(SymptomDict.id.in_(symptom_ids)).all()}

    unasked_sids = {
        sid for sid in symptom_ids
        if symptoms[sid].name not in asked_set
    }

    if not unasked_sids:
        return None

    d_s_map: dict[int, dict[int, SymptomDisease]] = {}
    for a in all_assocs:
        d_s_map.setdefault(a.disease_id, {})[a.symptom_id] = a

    confuser_sids: set[int] = set()
    confusers = db.query(DiseaseConfuser).all()
    top_id_set = set(top_ids)
    for cf in confusers:
        if cf.disease_a_id in top_id_set and cf.disease_b_id in top_id_set:
            for sid in (cf.distinguishing_symptom_ids or []):
                confuser_sids.add(sid)

    scored: list[dict] = []
    for sid in unasked_sids:
        sym = symptoms[sid]
        disc = 0.0
        is_req = False
        is_disc = False
        is_pos = True

        for i in range(len(top_ids)):
            for j in range(i + 1, len(top_ids)):
                di, dj = top_ids[i], top_ids[j]
                wi = d_s_map.get(di, {}).get(sid)
                wj = d_s_map.get(dj, {}).get(sid)
                weight_i = wi.weight if wi else 0
                weight_j = wj.weight if wj else 0
                disc += abs(weight_i - weight_j) * score_map[di] * score_map[dj]

                for w in (wi, wj):
                    if w:
                        if w.is_required:
                            is_req = True
                        if w.is_discriminative:
                            is_disc = True
                        if not w.is_positive:
                            is_pos = False

        if sid in confuser_sids:
            disc *= 1.5
        if is_disc:
            disc *= 1.3
        if is_req:
            disc *= 2.0
        if not is_pos:
            disc *= 0.8

        scored.append({
            "symptom_id": sid,
            "symptom_name": sym.name,
            "disc_score": round(disc, 6),
            "is_required": is_req,
        })

    if not scored:
        return None

    scored.sort(key=lambda x: x["disc_score"], reverse=True)
    best = scored[0]

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
        dep_id = next((c["department_id"] for c in effective if c["department_name"] == g["department_name"]), None)
        recommendations.append({
            "department": g["department_name"],
            "department_id": dep_id,
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
