"""
NER 训练数据增强脚本
基于 seed_data.py 中 159 个症状的别名，批量生成带标注的训练样本。
用法: python augment_ner_data.py [--count 500]
"""

import json, os, sys, random, argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 口语化表达模板（{symptom} 将被替换为症状名或别名）
TEMPLATES = [
    "我最近{symptom}，挺难受的。",
    "{symptom}好几天了，一直没好。",
    "主要是{symptom}，还有点{symptom2}。",
    "从昨天开始{symptom}，越来越严重。",
    "{symptom}，{symptom2}，晚上都睡不好。",
    "这几天{symptom}得厉害，{symptom2}也有。",
    "老是{symptom}，反反复复的。",
    "{symptom}，有时候还会{symptom2}。",
    "最难受的就是{symptom}，{symptom2}倒还好。",
    "感觉{symptom}，另外{symptom2}也比较明显。",
    "医生，我{symptom}，{symptom2}，这种情况怎么办？",
    "请问{symptom}，伴随着{symptom2}，是什么问题？",
    "大概一周了，{symptom}和{symptom2}断断续续的。",
    "{symptom}特别严重，{symptom2}倒是轻微。",
    "就是{symptom}，然后{symptom2}，没别的了。",
    "刚开始只是{symptom}，后来{symptom2}也出现了。",
    "我妈{symptom}，我爸也{symptom}，遗传的吗？",
    "{symptom}，而且{symptom2}，要挂哪个科？",
    "有点{symptom}，很{symptom2}，但不{symptom3}。",
    "其实主要是{symptom}，偶尔{symptom2}，不太{symptom3}。",
    "感冒好了以后一直{symptom}，还{symptom2}。",
    "最近压力大，{symptom}和{symptom2}都犯了。",
    "吃完饭后{symptom}，过一会{symptom2}。",
    "运动后{symptom}加重，休息时{symptom2}。",
    "早上起来{symptom}，到了晚上{symptom2}。",
]

# 连接词（用于自然连接多个症状）
CONNECTORS = ["，", "，还", "，而且", "，另外", "，同时还", "，并伴有", "，有时", "，偶尔"]


def load_symptom_aliases():
    """从数据库加载所有症状及其别名。"""
    from app.database import SessionLocal
    from app.models.symptom_dict import SymptomDict

    db = SessionLocal()
    try:
        symptoms = db.query(SymptomDict).all()
        result = {}
        for sym in symptoms:
            names = [sym.name]
            if sym.aliases:
                names.extend(a.strip() for a in sym.aliases.split(",") if a.strip())
            result[sym.name] = names
        return result
    finally:
        db.close()


def load_existing_samples():
    """加载已有标注数据中的实体名集合，避免重复。"""
    path = os.path.join(os.path.dirname(__file__), "annotated_symptoms.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        existing_texts = {d["text"] for d in data}
        return data, existing_texts
    return [], set()


def generate_samples(symptom_aliases: dict, count: int, existing_texts: set) -> list[dict]:
    """生成新的标注样本，在模板替换时精确追踪实体位置。"""
    # 建立 别名→标准名 的反向映射 (只保留长度 ≥ 2 的别名避免误匹配)
    alias_to_canonical = {}
    for canonical, aliases in symptom_aliases.items():
        for alias in aliases:
            if len(alias) >= 2:  # 过滤单字别名，避免误匹配
                alias_to_canonical[alias] = canonical

    all_aliases_pool = list(alias_to_canonical.keys())

    samples = []
    max_attempts = count * 15
    attempts = 0

    while len(samples) < count and attempts < max_attempts:
        attempts += 1

        # 随机选 1-3 个不同症状
        num_symptoms = random.randint(1, 3)
        if len(all_aliases_pool) < num_symptoms:
            chosen_aliases = random.choices(all_aliases_pool, k=num_symptoms)
        else:
            chosen_aliases = random.sample(all_aliases_pool, num_symptoms)
        
        # 确保不是同一个规范名
        canonicals = [alias_to_canonical[a] for a in chosen_aliases]
        if len(set(canonicals)) < len(chosen_aliases):
            continue

        # 选模板
        template = random.choice(TEMPLATES)

        # 逐占位符替换并记录实体位置
        entities = []
        text = template
        
        # 按占位符从后往前替换，保持前面位置不变
        placeholders = ["symptom3", "symptom2", "symptom"]
        for i, ph in enumerate(placeholders):
            marker = "{" + ph + "}"
            if marker not in text:
                continue
            idx = len(placeholders) - 1 - i  # symptom=0, symptom2=1, symptom3=2
            if idx < len(chosen_aliases):
                alias = chosen_aliases[idx]
                canonical = alias_to_canonical[alias]
                pos = text.find(marker)
                if pos >= 0:
                    text = text[:pos] + alias + text[pos + len(marker):]
                    entities.append({
                        "start_idx": pos,
                        "end_idx": pos + len(alias),
                        "entity": canonical,
                    })

        # 清理残留占位符
        import re
        text = re.sub(r'\{symptom\d?\}', '', text)
        text = re.sub(r'，,+', '，', text)
        text = re.sub(r'。，', '。', text)
        text = text.strip()

        if not text or len(text) < 4:
            continue
        if text in existing_texts:
            continue

        if entities:
            entities.sort(key=lambda e: e["start_idx"])
            samples.append({"text": text, "entities": entities})
            existing_texts.add(text)

    return samples


def main():
    parser = argparse.ArgumentParser(description="Augment NER training data")
    parser.add_argument("--count", type=int, default=300, help="Number of new samples to generate (default: 300)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not save")
    args = parser.parse_args()

    print(f"Loading symptom aliases from database...")
    symptom_aliases = load_symptom_aliases()
    print(f"  {len(symptom_aliases)} canonical symptoms, "
          f"{sum(len(v) for v in symptom_aliases.values())} total aliases")

    print(f"Loading existing annotations...")
    existing_data, existing_texts = load_existing_samples()
    print(f"  {len(existing_data)} existing samples")

    print(f"Generating {args.count} new samples...")
    new_samples = generate_samples(symptom_aliases, args.count, existing_texts)
    print(f"  Generated {len(new_samples)} samples")

    if args.dry_run:
        print("\n--- Preview (first 5) ---")
        for s in new_samples[:5]:
            print(f"  {s['text']}")
            for e in s['entities']:
                print(f"    [{e['start_idx']}:{e['end_idx']}] {e['entity']}")
        return

    # Merge and save
    all_data = existing_data + new_samples
    out_path = os.path.join(os.path.dirname(__file__), "annotated_symptoms.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    total_entities = sum(len(d["entities"]) for d in all_data)
    unique_symptoms = len({e["entity"] for d in all_data for e in d["entities"]})
    print(f"\nSaved {len(all_data)} samples ({len(existing_data)} existing + {len(new_samples)} new)")
    print(f"  Total entities: {total_entities}")
    print(f"  Unique symptom types: {unique_symptoms}")
    print(f"  File: {out_path}")


if __name__ == "__main__":
    main()
