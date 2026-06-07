import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(MODEL_DIR, "data")

COLLOQUIAL_TEMPLATES = [
    ("最近总是{s}", "最近一直{s}"),
    ("{s}好几天了", "{s}好久了"),
    ("{s}得厉害", "{s}很严重"),
    ("有点{s}", "稍微有点{s}"),
    ("{s}，还有点恶心", "{s}，晚上也睡不好"),
    ("{s}越来越严重了", "{s}比昨天更厉害了"),
    ("从昨天开始{s}", "前几天开始{s}"),
    ("{s}，特别难受", "{s}，感觉不太对"),
    ("主要是{s}", "最明显就是{s}"),
    ("{s1}和{s2}一起出现", "{s1}，有时候还{s2}"),
    ("{s}，吃了药也没用", "{s}，打过针也不见效"),
    ("{s}一阵一阵的", "{s}间歇性的"),
    ("左边{s}，右边没事", "右边{s}得比较多"),
    ("{s}，一躺下就加重", "{s}，活动一下就好点"),
    ("不怎么{s}，就是{s2}比较明显", "没有{s}，但{s2}很明显"),
]

TYPO_MAP = {
    "头痛": "头庝", "发烧": "发繞", "咳嗽": "咳漱", "呕吐": "沤吐",
    "腹泻": "腹泄", "乏力": "伐力", "头晕": "头昏", "咽痛": "咽喉痛",
    "鼻塞": "鼻堵", "胸闷": "胸焖",
}


def generate_template_data(symptom_dict: list[dict]) -> list[dict]:
    """从症状字典生成口语化模板训练数据"""
    samples = []
    rng = random.Random(42)

    for sym in symptom_dict:
        name = sym["name"]
        aliases = [a.strip() for a in sym.get("aliases", "").split(",") if a.strip()]
        all_names = [name] + aliases[:2]

        for i, tmpl in enumerate(COLLOQUIAL_TEMPLATES):
            variant = rng.choice(tmpl)
            main_name = rng.choice(all_names)

            if "{s1}" in variant and "{s2}" in variant:
                other = all_names[1] if len(all_names) > 1 else name
                text = variant.replace("{s1}", main_name).replace("{s2}", other)
            elif "{s}" in variant:
                text = variant.replace("{s}", main_name)
            else:
                text = variant.replace("{s}", main_name)

            has_typo = rng.random() < 0.1 and name in TYPO_MAP
            if has_typo:
                text = text.replace(name, TYPO_MAP[name])

            entities = find_symptom_entities(text, all_names)
            if entities:
                samples.append({"text": text, "entities": entities, "source": "template"})

    return samples


def find_symptom_entities(text: str, search_terms: list[str]) -> list[dict]:
    entities = []
    positions = []
    for term in search_terms:
        idx = 0
        while True:
            idx = text.find(term, idx)
            if idx == -1:
                break
            positions.append((idx, idx + len(term) - 1))
            idx += 1

    positions.sort()
    merged = []
    for start, end in positions:
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))

    for start, end in merged:
        entities.append({
            "start_idx": start, "end_idx": end,
            "type": "sym", "entity": text[start:end + 1],
        })
    return entities


def load_symptom_dict() -> list[dict]:
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
        aliases = (s.aliases or "")
        syn_terms = syn_map.get(s.id, [])
        if syn_terms:
            aliases += "," + ",".join(syn_terms)
        result.append({"name": s.name, "aliases": aliases})
    db.close()
    return result


def load_cmee_sym_only(cmee_path: str) -> list[dict]:
    with open(cmee_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    samples = []
    for item in raw:
        text = item["text"]
        sym_entities = [e for e in item.get("entities", []) if e["type"] in ("sym",)]
        if sym_entities:
            samples.append({"text": text, "entities": sym_entities, "source": "cmee"})
    return samples


def build_datasets():
    os.makedirs(DATA_DIR, exist_ok=True)

    from download_data import download_cmee, RAW_DIR
    download_cmee()

    # CMeEE
    cmee_train = load_cmee_sym_only(os.path.join(RAW_DIR, "CMeEE-V2_train.json"))
    cmee_dev = load_cmee_sym_only(os.path.join(RAW_DIR, "CMeEE-V2_dev.json"))

    # Template
    symptoms = load_symptom_dict()
    template = generate_template_data(symptoms)

    rng = random.Random(42)
    rng.shuffle(template)
    split = int(len(template) * 0.8)

    # Merge
    train = cmee_train + template[:split]
    dev = cmee_dev + template[split:]

    rng.shuffle(train)
    rng.shuffle(dev)

    with open(os.path.join(DATA_DIR, "train.json"), "w", encoding="utf-8") as f:
        json.dump(train, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA_DIR, "dev.json"), "w", encoding="utf-8") as f:
        json.dump(dev, f, ensure_ascii=False, indent=2)

    print(f"数据集生成完成:")
    print(f"  train: {len(train)} 条 (cmee={len(cmee_train)}, template={len(template[:split])})")
    print(f"  dev:   {len(dev)} 条 (cmee={len(cmee_dev)}, template={len(template[split:])})")


if __name__ == "__main__":
    build_datasets()
