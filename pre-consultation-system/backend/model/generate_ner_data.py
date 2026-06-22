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
    # 新增口语模板
    ("就是{s}，也不知道怎么回事", "老感觉{s}，也不知道啥原因"),
    ("{s}得不行，整晚睡不着", "{s}得厉害，觉都睡不好"),
    ("{s}反反复复的，好了又犯", "{s}时好时坏，没断根"),
    ("主要症状就是{s}", "主要就是{s}难受"),
    ("{s}有点严重", "{s}比以前重多了"),
    ("动不动就{s}", "经常{s}，尤其是晚上"),
    ("{s}的时候特别难受", "{s}起来真要命"),
    ("一开始就是{s}", "最开始只是有点{s}"),
    ("{s}老不好，都拖了好久了", "{s}一直没好利索"),
    ("可能是{s}吧，也不确定", "感觉像是{s}，不太确定"),
    ("{s1}的时候还带着{s2}", "{s1}，连着{s2}也不舒服"),
    ("除了{s1}，还有{s2}", "{s1}，{s2}也挺明显的"),
    ("{s1}，然后就开始{s2}了", "先是{s1}，后来变成{s2}"),
    ("{s}，走路都受影响", "{s}得走不动路"),
    ("一干活就{s}", "一活动就{s}得更厉害"),
    ("{s}反反复复的", "{s}没断过，一直有"),
    ("{s}，冷热都难受", "{s}，风一吹更不舒服"),
    ("{s}，吃饭也没胃口", "{s}得饭都吃不下"),
    ("{s}，心里老惦记着", "{s}，让人特别烦"),
    ("就是有点{s}，别的倒还好", "{s}有一点，不算太严重"),
    ("{s}十来天了", "{s}快半个月了"),
    ("{s}，不敢动", "{s}，一动就疼"),
    ("{s}得直冒汗", "{s}，额头上都是汗"),
    ("{s1}，偶尔还会{s2}", "{s1}，有时候{s2}一下"),
    ("{s}，坐着还好，站起来就难受", "{s}，躺平了能好点"),
    ("{s1}和{s2}都有", "{s1}伴{s2}"),
    ("{s}，说不出是什么感觉", "{s}，形容不上来"),
    ("{s}，一阵阵的", "{s}一会儿轻一会儿重"),
    ("{s}，吃了药能缓解一点", "{s}，吃药能管一会儿"),
    ("老毛病了，{s}", "以前就有这个问题，{s}"),
]

TYPO_MAP = {
    "头痛": "头庝", "发烧": "发繞", "咳嗽": "咳漱", "呕吐": "沤吐",
    "腹泻": "腹泄", "乏力": "伐力", "头晕": "头昏", "咽痛": "咽喉痛",
    "鼻塞": "鼻堵", "胸闷": "胸焖",
}


def generate_template_data(symptom_dict: list[dict], target_count: int = 2500) -> list[dict]:
    """从症状字典生成口语化模板训练数据，目标 target_count 条"""
    samples = []
    rng = random.Random(42)

    for sym in symptom_dict:
        name = sym["name"]
        aliases = [a.strip() for a in sym.get("aliases", "").split(",") if a.strip()]
        all_names = [name] + aliases[:5]

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

    while len(samples) < target_count:
        sym = rng.choice(symptom_dict)
        name = sym["name"]
        aliases = [a.strip() for a in sym.get("aliases", "").split(",") if a.strip()]
        all_names = [name] + aliases[:5]
        tmpl = rng.choice(COLLOQUIAL_TEMPLATES)
        variant = rng.choice(tmpl)
        main_name = rng.choice(all_names)
        if "{s1}" in variant and "{s2}" in variant:
            other = all_names[1] if len(all_names) > 1 else name
            text = variant.replace("{s1}", main_name).replace("{s2}", other)
        elif "{s}" in variant:
            text = variant.replace("{s}", main_name)
        else:
            text = variant.replace("{s}", main_name)
        entities = find_symptom_entities(text, all_names)
        if entities:
            samples.append({"text": text, "entities": entities, "source": "template"})

    return samples[:target_count]


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


def build_search_index(symptom_dict: list[dict]) -> dict:
    index = {}
    for sym in symptom_dict:
        name = sym["name"]
        aliases = [a.strip() for a in sym.get("aliases", "").split(",") if a.strip()]
        for term in [name] + aliases:
            if term not in index:
                index[term] = []
            index[term].append(sym["name"])
    return index


def auto_label_meddialog(sentences: list[str], search_index: dict) -> list[dict]:
    samples = []
    for text in sentences:
        entities = []
        positions = []
        for term, sym_names in search_index.items():
            idx = 0
            while True:
                idx = text.find(term, idx)
                if idx == -1:
                    break
                prev = text[idx - 1] if idx > 0 else ""
                next_c = text[idx + len(term)] if idx + len(term) < len(text) else ""
                if prev.isalpha() or prev.isdigit() or next_c.isalpha() or next_c.isdigit():
                    idx += len(term)
                    continue
                sym_name = sym_names[0]
                positions.append((idx, idx + len(term) - 1, sym_name))
                idx += len(term)
        positions.sort()
        seen = set()
        for start, end, sym_name in positions:
            key = f"{start}-{end}"
            if key not in seen:
                entities.append({
                    "start_idx": start, "end_idx": end,
                    "type": "sym", "entity": sym_name,
                })
                seen.add(key)
        if entities:
            samples.append({"text": text, "entities": entities, "source": "meddialog"})
    return samples


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


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_datasets():
    os.makedirs(DATA_DIR, exist_ok=True)

    from model.download_data import load_annotated

    rng = random.Random(42)

    # Annotated (33 manual) — 26 train / 7 dev
    annotated = load_annotated()
    rng.shuffle(annotated)
    ann_split = max(1, int(len(annotated) * 0.8))
    ann_train = annotated[:ann_split]
    ann_dev = annotated[ann_split:]

    # Augmented (970 from augment_data.py) — 80% train / 20% dev
    aug_path = os.path.join(MODEL_DIR, "data", "augmented.json")
    augmented = load_json(aug_path) if os.path.exists(aug_path) else []
    rng.shuffle(augmented)
    aug_split = int(len(augmented) * 0.8)
    aug_train = augmented[:aug_split]
    aug_dev = augmented[aug_split:]

    # Template (3500 from DB) — 80% train / 20% dev
    symptoms = load_symptom_dict()
    template = generate_template_data(symptoms, target_count=3500)
    rng.shuffle(template)
    tpl_split = int(len(template) * 0.8)
    tpl_train = template[:tpl_split]
    tpl_dev = template[tpl_split:]

    # Merge — NO CMeEE
    train = ann_train + aug_train + tpl_train
    dev = ann_dev + aug_dev + tpl_dev

    rng.shuffle(train)
    rng.shuffle(dev)

    with open(os.path.join(DATA_DIR, "train.json"), "w", encoding="utf-8") as f:
        json.dump(train, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA_DIR, "dev.json"), "w", encoding="utf-8") as f:
        json.dump(dev, f, ensure_ascii=False, indent=2)

    print(f"\n数据集生成完成 (不含CMeEE):")
    print(f"  train: {len(train)} 条")
    print(f"    augmented:  {len(aug_train)}")
    print(f"    annotated:  {len(ann_train)}")
    print(f"    template:   {len(tpl_train)}")
    print(f"  dev:   {len(dev)} 条")
    print(f"    augmented:  {len(aug_dev)}")
    print(f"    annotated:  {len(ann_dev)}")
    print(f"    template:   {len(tpl_dev)}")


if __name__ == "__main__":
    build_datasets()
