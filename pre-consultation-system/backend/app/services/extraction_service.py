from sqlalchemy.orm import Session
from app.services.symptom_extractor import match_keywords, extract_bert
from app.config import settings
from app.logger import logger


def extract_symptoms(text: str, db: Session) -> list[dict]:
    """
    统一症状提取入口。
    按 AI_MODE 选择：
    - degrade: 仅关键词匹配
    - bert: BERT NER 优先，降级到关键词
    - full: BERT NER 优先，降级到关键词（DeepSeek 在后续阶段使用）
    """
    if settings.AI_MODE in ("degrade", "bert", "full"):
        logger.debug("症状提取模式: %s", settings.AI_MODE)
    else:
        logger.warning("未知 AI_MODE=%s，使用 degrade", settings.AI_MODE)

    if settings.AI_MODE == "degrade":
        return match_keywords(text, db)

    bert_results = extract_bert(text)
    if bert_results:
        logger.debug("BERT NER 提取到 %d 个症状", len(bert_results))
        return bert_results
    logger.debug("BERT 未启用或无结果，降级到关键词匹配")
    return match_keywords(text, db)


def extract_from_description(description: str, db: Session) -> list[dict]:
    if not description or not description.strip():
        return []
    return extract_symptoms(description.strip(), db)
