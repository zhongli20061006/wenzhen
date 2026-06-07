from sqlalchemy.orm import Session
from app.services.symptom_extractor import match_keywords, extract_bert


def extract_symptoms(text: str, db: Session) -> list[dict]:
    """
    统一症状提取入口：
    优先 BERT NER，未启用时降级到关键词匹配。
    """
    bert_results = extract_bert(text)
    if bert_results:
        return bert_results
    return match_keywords(text, db)


def extract_from_description(description: str, db: Session) -> list[dict]:
    """
    从自由文本描述中提取症状。
    """
    if not description or not description.strip():
        return []
    return extract_symptoms(description.strip(), db)
