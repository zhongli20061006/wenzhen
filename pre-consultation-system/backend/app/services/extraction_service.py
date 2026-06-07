from sqlalchemy.orm import Session
from app.services.symptom_extractor import match_keywords, extract_bert
from app.config import settings
from app.logger import logger


def extract_symptoms(text: str, db: Session) -> list[dict]:
    """
    统一症状提取入口。
    degrade 模式: 关键词/别名/同义词匹配
    bert/full: 同上（当前通用NER模型不含医学标签，后续可替换医学NER模型）
    """
    mode = settings.AI_MODE or "degrade"
    logger.debug("症状提取模式: %s", mode)

    if mode == "degrade":
        return match_keywords(text, db)

    bert_results = extract_bert(text)
    if bert_results:
        logger.debug("BERT NER 提取到 %d 个症状", len(bert_results))
        return bert_results
    logger.debug("BERT 无结果，降级到关键词匹配")
    return match_keywords(text, db)


def extract_from_description(description: str, db: Session) -> list[dict]:
    if not description or not description.strip():
        return []
    return extract_symptoms(description.strip(), db)
