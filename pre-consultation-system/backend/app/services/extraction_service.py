import asyncio
from sqlalchemy.orm import Session
from app.services.symptom_extractor import match_keywords, extract_bert
from app.config import settings
from app.logger import logger


def extract_symptoms(text: str, db: Session) -> list[dict]:
    """
    统一症状提取入口 — NER + 关键词双引擎融合。
    NER 模型精度高但召回偏低（训练数据有限），关键词召回全面。
    两者合并去重，NER 结果优先级更高。

    NOTE: NER 模型现可提取 BODY/DRUG/TIME 实体类型，但目前仅 SYMPTOM
    实体用于症状-字典匹配（map_to_symptom_dict），BODY/DRUG/TIME 实体
    以原样返回（含 type 字段），可供后续扩展使用。
    """
    bert_results = extract_bert(text)

    # 关键词匹配作为补充
    kw_results = match_keywords(text, db)

    # 合并去重：以 symptom_id 为键，NER 优先
    merged: dict[int, dict] = {}
    # 先放关键词结果（低优先级）
    for r in kw_results:
        sid = r["symptom_id"]
        merged.setdefault(sid, r)
        merged[sid]["source"] = "keyword"
    # NER 结果覆盖（高优先级）
    for r in bert_results:
        sid = r["symptom_id"]
        merged[sid] = r
        merged[sid]["source"] = "ner"

    if bert_results:
        ner_ids = {r["symptom_id"] for r in bert_results}
        logger.info("症状提取: NER=%d, 关键词=%d, 合并=%d",
                     len(bert_results), len(kw_results), len(merged))
    else:
        logger.info("症状提取: 关键词=%d (NER 不可用)", len(kw_results))

    return list(merged.values())


async def extract_from_description_async(description: str, db: Session) -> list[dict]:
    """异步版本：将 NER 模型推理放入线程池，避免阻塞事件循环"""
    if not description or not description.strip():
        return []
    text = description.strip()
    # 关键词匹配（轻量，同步执行）
    kw_results = match_keywords(text, db)
    # NER 模型推理放入线程池（避免阻塞事件循环）
    bert_results = await asyncio.to_thread(extract_bert, text)
    # 合并去重
    merged: dict[int, dict] = {}
    for r in kw_results:
        sid = r["symptom_id"]
        merged.setdefault(sid, r)
        merged[sid]["source"] = "keyword"
    for r in bert_results:
        sid = r["symptom_id"]
        merged[sid] = r
        merged[sid]["source"] = "ner"
    if bert_results:
        logger.info("症状提取: NER=%d, 关键词=%d, 合并=%d",
                     len(bert_results), len(kw_results), len(merged))
    else:
        logger.info("症状提取: 关键词=%d (NER 不可用)", len(kw_results))
    return list(merged.values())


def extract_from_description(description: str, db: Session) -> list[dict]:
    """同步版本（向后兼容）：直接从描述文本提取症状"""
    if not description or not description.strip():
        return []
    return extract_symptoms(description.strip(), db)
