import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
ANNOTATED_PATH = os.path.join(MODEL_DIR, "annotated_symptoms.json")

MODIFIERS = ["有点", "有点儿", "有些", "有一些", "稍微有点", "挺", "很", "特别", "非常", "相当", "好", "蛮"]
TIME_PATTERNS = [
    ("了三天了", ["了几天", "了好几天了", "快一周了", "十来天了", "好久了", "有一阵了"]),
    ("好几天了", ["好久了", "很长一段时间了", "有一阵子了", "快半个月了", "都几周了"]),
    ("这两天", ["最近几天", "这几天", "最近一阵子", "这一阵", "这几天了"]),
    ("一直", ["老是", "总是", "动不动就", "经常", "反复", "持续的"]),
]
FILLER_PHRASES = [
    "也不知道怎么回事",
    "愁死我了",
    "也不知道是不是这个原因",
    "之前都好好的",
    "以前没有这种情况",
    "搞得我觉都睡不好",
    "去医院看过但没检查出啥",
    "心里老惦记着这事儿",
    "不知道要不要紧",
    "想问问这什么情况",
]


def load_annotated():
    with open(ANNOTATED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_symptom_dict():
    from app.database import SessionLocal
    from app.models.symptom_dict import SymptomDict
    from app.models.symptom_synonym import SymptomSynonym

    db = SessionLocal()
    symptoms = db.query(SymptomDict).all()
    synonyms = db.query(SymptomSynonym).all()

    syn_map = {}
    for s in synonyms:
        syn_map.setdefault(s.symptom_id, []).append(s.term)

    result = []
    for s in symptoms:
        aliases = [a.strip() for a in (s.aliases or "").split(",") if a.strip()]
        syn_terms = syn_map.get(s.id, [])
        all_aliases = list(dict.fromkeys(aliases + syn_terms))
        result.append({
            "id": s.id,
            "name": s.name,
            "aliases": all_aliases,
        })
    db.close()
    return result


def substitute_symptom(text: str, old: str, new: str, start: int, end: int, entities: list) -> tuple:
    new_text = text[:start] + new + text[end + 1:]
    delta = len(new) - (end - start + 1)
    new_entities = []
    for e in entities:
        e2 = dict(e)
        if e2["start_idx"] == start and e2["end_idx"] == end:
            e2["entity"] = new
            e2["end_idx"] = start + len(new) - 1
        else:
            if e2["start_idx"] > end:
                e2["start_idx"] += delta
            if e2["end_idx"] > end:
                e2["end_idx"] += delta
        new_entities.append(e2)
    return new_text, new_entities


def apply_modifier(text: str) -> str:
    import re
    for m in MODIFIERS:
        pattern = m + "|" + m.replace("点儿", "点")
    mod_from = random.choice(MODIFIERS)
    mod_to = random.choice([m for m in MODIFIERS if m != mod_from])
    return text.replace(mod_from, mod_to)


def apply_time_variation(text: str) -> str:
    for old, variants in TIME_PATTERNS:
        if old in text:
            return text.replace(old, random.choice(variants))
    return text


def insert_modifier(text: str) -> tuple:
    positions = []
    for i, c in enumerate(text):
        if c in "，。！？、；：\n":
            continue
        prev = text[i-1:i]
        if prev and prev != '，' and not prev.isspace():
            continue
        positions.append(i)
    if not positions or len(positions) < 2:
        return text, []
    pos = random.choice(positions[1:])
    mod = random.choice(MODIFIERS)
    new_text = text[:pos] + mod + text[pos:]
    return new_text, [(pos, len(mod))]


def apply_filler(text: str) -> str:
    if random.random() < 0.3:
        return text + random.choice(FILLER_PHRASES)
    if random.random() < 0.15:
        return random.choice(FILLER_PHRASES) + "，" + text
    return text


def augment():
    rng = random.Random(42)
    annotated = load_annotated()
    symptoms = load_symptom_dict()
    sym_by_name = {s["name"]: s for s in symptoms}
    all_terms = [(s["name"], s["aliases"]) for s in symptoms]

    print(f"种子数据: {len(annotated)} 条")
    print(f"症状库: {len(symptoms)} 个")

    augmented = list(annotated)

    for seed in annotated:
        seed_entities = seed["entities"]
        seed_sym_names = [e["entity"] for e in seed_entities]

        # Strategy 1: symptom substitution (target: ~12 per seed)
        for _ in range(12):
            if not seed_sym_names:
                break
            target_entity = rng.choice(seed_entities)
            old_name = target_entity["entity"]
            idx = rng.randrange(len(all_terms))
            new_name, new_aliases = all_terms[idx]
            if new_name == old_name:
                continue
            new_text, new_entities = substitute_symptom(
                seed["text"], old_name, new_name,
                target_entity["start_idx"], target_entity["end_idx"], seed_entities,
            )
            augmented.append({
                "text": new_text, "entities": new_entities, "source": "aug_substitute",
            })

        # Strategy 2: alias substitution (target: ~6 per seed)
        for _ in range(6):
            valid = [(e, sn) for e in seed_entities if (sn := e["entity"]) in sym_by_name
                     and sym_by_name[sn]["aliases"]]
            if not valid:
                break
            target_entity, old_name = rng.choice(valid)
            alias = rng.choice(sym_by_name[old_name]["aliases"])
            new_text, new_entities = substitute_symptom(
                seed["text"], old_name, alias,
                target_entity["start_idx"], target_entity["end_idx"], seed_entities,
            )
            augmented.append({
                "text": new_text, "entities": new_entities, "source": "aug_alias",
            })

        # Strategy 3: modifier variation + injection (target: ~3 per seed)
        for _ in range(3):
            new_text = apply_modifier(seed["text"])
            if new_text != seed["text"]:
                augmented.append({
                    "text": new_text, "entities": seed["entities"], "source": "aug_modifier",
                })
            else:
                new_text, _ = insert_modifier(seed["text"])
                if new_text != seed["text"]:
                    augmented.append({
                        "text": new_text, "entities": seed["entities"], "source": "aug_modifier",
                    })

        # Strategy 4: time expression variation (target: ~2 per seed)
        for _ in range(2):
            new_text = apply_time_variation(seed["text"])
            if new_text != seed["text"]:
                augmented.append({
                    "text": new_text, "entities": seed["entities"], "source": "aug_time",
                })

        # Strategy 5: filler injection (target: ~2 per seed)
        for _ in range(2):
            new_text = apply_filler(seed["text"])
            if new_text != seed["text"]:
                augmented.append({
                    "text": new_text, "entities": seed["entities"], "source": "aug_filler",
                })

    # Strategy 6: multi-symptom recombination
    for _ in range(300):
        s1 = rng.choice(annotated)
        s2 = rng.choice(annotated)
        if s1["text"] == s2["text"]:
            continue
        e1 = rng.choice(s1["entities"])
        e2 = rng.choice(s2["entities"])
        connectors = [f"，{e2['entity']}也有", f"，而且{e2['entity']}", f"，另外还有{e2['entity']}",
                      f"，{e2['entity']}也挺明显", f"，连着{e2['entity']}也不舒服"]
        suffix = rng.choice(connectors)
        new_text = s1["text"] + suffix
        new_entities = list(s1["entities"]) + [{
            "start_idx": len(s1["text"]) + 1,
            "end_idx": len(s1["text"]) + 1 + len(e2["entity"]) - 1,
            "type": "sym",
            "entity": e2["entity"],
        }]
        augmented.append({
            "text": new_text, "entities": new_entities, "source": "aug_merge",
        })

    # Deduplicate by text
    seen = set()
    unique = []
    for item in augmented:
        if item["text"] not in seen:
            seen.add(item["text"])
            unique.append(item)

    rng.shuffle(unique)

    out_path = os.path.join(MODEL_DIR, "data", "augmented.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    # Stats
    sources = {}
    for item in unique:
        s = item.get("source", "annotated")
        sources[s] = sources.get(s, 0) + 1
    print(f"\n增广完成: {len(unique)} 条 (原始 {len(annotated)} 条)")
    for k, v in sorted(sources.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    augment()
