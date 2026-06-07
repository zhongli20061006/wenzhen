from sqlalchemy.orm import Session
from app.models.symptom_dict import SymptomDict
from app.models.symptom_synonym import SymptomSynonym


def match_keywords(text: str, db: Session) -> list[dict]:
    """
    关键词/别名匹配提取症状。
    比 standardize_symptoms 多一层 synonym 表匹配。
    返回 [{symptom_id, symptom_name, match_type, confidence}]。
    """
    results: dict[int, dict] = {}
    symptoms = db.query(SymptomDict).all()
    sym_map = {s.id: s for s in symptoms}

    for sym in symptoms:
        name = sym.name
        if name and name in text:
            results.setdefault(sym.id, {
                "symptom_id": sym.id, "symptom_name": name, "match_type": "name", "confidence": 1.0
            })
            continue
        if sym.aliases:
            for alias in sym.aliases.split(","):
                alias = alias.strip()
                if alias and alias in text:
                    results.setdefault(sym.id, {
                        "symptom_id": sym.id, "symptom_name": name, "match_type": "alias", "confidence": 0.95
                    })
                    break

    synonyms = db.query(SymptomSynonym).all()
    for syn in synonyms:
        if syn.symptom_id in results:
            continue
        if syn.term in text:
            sym = sym_map.get(syn.symptom_id)
            if sym:
                results[syn.symptom_id] = {
                    "symptom_id": sym.id, "symptom_name": sym.name,
                    "match_type": "synonym", "confidence": round(syn.weight, 2),
                }

    return list(results.values())


def extract_bert(text: str) -> list[dict]:
    """
    PyTorch BERT NER 提取症状（Phase 2.1b 实现）。
    当前返回空列表，表示未启用；调用方应 degrade 到 match_keywords。
    """
    return []
