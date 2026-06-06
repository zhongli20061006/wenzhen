from typing import Optional
from sqlalchemy.orm import Session

from app.models.symptom_dict import SymptomDict


def alias_match(text: str, db: Session) -> list[dict]:
    """
    根据输入文本中的症状关键词，通过别名表匹配标准症状。
    返回 [{symptom_id, symptom_name, match_type}]。
    """
    results = []
    symptoms = db.query(SymptomDict).all()
    text_lower = text.lower()

    for sym in symptoms:
        if sym.name and sym.name.lower() in text_lower:
            results.append({
                "symptom_id": sym.id,
                "symptom_name": sym.name,
                "match_type": "exact",
            })
            continue
        if sym.aliases:
            for alias in sym.aliases.split(","):
                alias = alias.strip()
                if alias and alias.lower() in text_lower:
                    results.append({
                        "symptom_id": sym.id,
                        "symptom_name": sym.name,
                        "match_type": "alias",
                    })
                    break

    return results


def standardize_symptoms(text: str, db: Session) -> list[dict]:
    """
    症状标准化入口。
    当前阶段：别名匹配。
    第二阶段：调用 PyTorch BERT 模型。
    """
    try:
        return ai_extract(text)
    except (ImportError, Exception):
        return alias_match(text, db)


def ai_extract(text: str) -> list[dict]:
    """
    AI 症状提取预留接口。
    第二阶段实现：加载 BERT-base-chinese 模型进行 NER/分类。
    """
    raise ImportError("AI 模块尚未集成")
