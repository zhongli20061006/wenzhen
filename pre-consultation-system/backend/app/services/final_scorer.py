from app.logger import logger


RULE_WEIGHT = 0.55
DEEPSEEK_WEIGHT = 0.45
AGREEMENT_BOOST = 0.10
CONFLICT_THRESHOLD = 0.30
EMERGENCY_TOP_K = 3


def compute_agreement(rule_scores: dict, ds_scores: dict) -> float:
    """
    计算规则引擎与DeepSeek对Top-K疾病排序的一致性(0-1)。
    使用 Kendall Tau 简化版。
    """
    all_names = list(set(rule_scores.keys()) | set(ds_scores.keys()))
    if len(all_names) <= 1:
        return 1.0

    rule_ranked = sorted(all_names, key=lambda n: rule_scores.get(n, 0), reverse=True)
    ds_ranked = sorted(all_names, key=lambda n: ds_scores.get(n, 0), reverse=True)

    rule_pos = {name: i for i, name in enumerate(rule_ranked)}
    ds_pos = {name: i for i, name in enumerate(ds_ranked)}

    concordant = 0
    discordant = 0
    for i in range(len(all_names)):
        for j in range(i + 1, len(all_names)):
            a, b = all_names[i], all_names[j]
            r_a, r_b = rule_pos[a], rule_pos[b]
            d_a, d_b = ds_pos[a], ds_pos[b]
            if (r_a < r_b and d_a < d_b) or (r_a > r_b and d_a > d_b):
                concordant += 1
            elif (r_a < r_b and d_a > d_b) or (r_a > r_b and d_a < d_b):
                discordant += 1

    total = concordant + discordant
    if total == 0:
        return 0.5
    tau = (concordant - discordant) / total
    return max(0.0, min(1.0, tau))


def apply_safety_overrides(merged: list[dict], rule_candidates: list[dict]) -> list[dict]:
    """
    安全规则：
    1. 任何紧急性为'紧急'的疾病必须排在前3位。
    2. 规则引擎中score>0.6的疾病不能被完全移除。
    """
    emergency_names = {
        c["disease_name"] for c in rule_candidates
        if c.get("urgency") == "紧急"
    }
    high_conf_names = {
        c["disease_name"] for c in rule_candidates
        if c.get("score", 0) > 0.6
    }

    others = []
    emergency_items = []
    high_conf_items = []

    for item in merged:
        name = item["disease_name"]
        if name in emergency_names:
            emergency_items.append(item)
        elif name in high_conf_names:
            high_conf_items.append(item)
        else:
            others.append(item)

    emergency_items.sort(key=lambda x: x["final_score"], reverse=True)
    high_conf_items.sort(key=lambda x: x["final_score"], reverse=True)
    others.sort(key=lambda x: x["final_score"], reverse=True)

    result = emergency_items[:EMERGENCY_TOP_K] + high_conf_items + others
    seen = set()
    deduped = []
    for item in result:
        if item["disease_name"] not in seen:
            deduped.append(item)
            seen.add(item["disease_name"])

    return deduped


def fuse_scores(rule_candidates: list[dict], deepseek_rankings: list[dict]) -> dict:
    """
    融合规则引擎与DeepSeek的疾病评分。

    流程：
    1. 加权融合: final = rule_weight * rule_score + ds_weight * ds_score
    2. 计算一致性: 若两者高度一致(>0.7)，统一加成
    3. 冲突检测: 若排名差异>CONFLICT_THRESHOLD，标记冲突
    4. 安全规则: 紧急疾病和高置信度疾病强制保留

    返回: {"merged": [...], "agreement": float, "conflicts": [...]}
    """
    rule_map = {}
    for c in rule_candidates:
        rule_map[c["disease_name"]] = {
            "score": c["score"],
            "dept_id": c.get("department_id"),
            "dept_name": c.get("department_name", ""),
            "urgency": c.get("urgency", "就诊"),
            "disease_id": c.get("disease_id"),
        }

    ds_map = {}
    for r in deepseek_rankings:
        ds_map[r.get("disease_name", "")] = r.get("adjusted_score", 0)

    rule_simple = {k: v["score"] for k, v in rule_map.items()}
    ds_simple = {k: v for k, v in ds_map.items()}

    agreement = compute_agreement(rule_simple, ds_simple)
    logger.info("规则引擎-DeepSeek一致性: %.3f", agreement)

    merged = []
    conflicts = []
    all_names = set(rule_map.keys()) | set(ds_map.keys())

    for name in all_names:
        rule_info = rule_map.get(name, {
            "score": 0, "urgency": "就诊", "dept_id": None, "dept_name": "", "disease_id": None,
        })
        rule_score = rule_info["score"]
        ds_score = ds_map.get(name, rule_score * 0.8)

        final_score = RULE_WEIGHT * rule_score + DEEPSEEK_WEIGHT * ds_score

        if agreement > 0.7:
            final_score += AGREEMENT_BOOST

        final_score = max(0.0, min(1.0, final_score))

        diff = abs(rule_score - ds_score)
        if diff > CONFLICT_THRESHOLD:
            conflicts.append({
                "disease_name": name,
                "rule_score": rule_score,
                "ds_score": ds_score,
                "diff": diff,
                "winner": "rule" if rule_score > ds_score else "deepseek",
            })

        merged.append({
            "disease_name": name,
            "disease_id": rule_info["disease_id"],
            "rule_score": rule_score,
            "ds_score": ds_score,
            "final_score": round(final_score, 4),
            "urgency": rule_info["urgency"],
            "department_id": rule_info["dept_id"],
            "department_name": rule_info["dept_name"],
            "deepseek_reasoning": next(
                (r.get("reasoning", "") for r in deepseek_rankings if r.get("disease_name") == name), ""),
        })

    merged.sort(key=lambda x: x["final_score"], reverse=True)
    merged = apply_safety_overrides(merged, rule_candidates)

    if conflicts:
        logger.warning("检测到%d个评分冲突: %s", len(conflicts),
                       ", ".join(c["disease_name"] for c in conflicts[:3]))

    return {
        "merged": merged,
        "agreement": round(agreement, 4),
        "conflicts": conflicts,
        "weights": {"rule": RULE_WEIGHT, "deepseek": DEEPSEEK_WEIGHT},
    }


def degrade_only(rule_candidates: list[dict]) -> dict:
    """
    降解模式：仅使用规则引擎结果。
    """
    merged = []
    for c in rule_candidates:
        merged.append({
            "disease_name": c["disease_name"],
            "disease_id": c.get("disease_id"),
            "rule_score": c["score"],
            "ds_score": 0,
            "final_score": c["score"],
            "urgency": c.get("urgency", "就诊"),
            "department_id": c.get("department_id"),
            "department_name": c.get("department_name", ""),
            "deepseek_reasoning": "",
        })
    merged.sort(key=lambda x: x["final_score"], reverse=True)
    merged = apply_safety_overrides(merged, rule_candidates)
    return {
        "merged": merged,
        "agreement": 1.0,
        "conflicts": [],
        "weights": {"rule": 1.0, "deepseek": 0.0},
        "mode": "degrade",
    }
