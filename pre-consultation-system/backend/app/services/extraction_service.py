import asyncio
from sqlalchemy.orm import Session
from app.services.symptom_extractor import match_keywords, extract_bert
from app.config import settings
from app.logger import logger


def _is_extraction_insufficient(results: list[dict]) -> bool:
    """判断 BERT+关键词 提取结果是否不足，需要触发 DeepSeek 保底。"""
    if len(results) < 2:
        return True
    confidences = [r.get("confidence", 0) for r in results]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    max_conf = max(confidences) if confidences else 0
    # 平均置信度低，或无高置信度命中 → 触发保底
    if avg_conf < 0.6 or max_conf < 0.8:
        return True
    return False


def _merge_deepseek_results(
    existing: list[dict],
    ds_results: list[dict],
) -> list[dict]:
    """
    将 DeepSeek 保底结果合并到已有结果中。
    优先级：NER > DeepSeek > 关键词
    """
    merged: dict[int, dict] = {}
    # 先放关键词结果（最低优先级）
    for r in existing:
        if r.get("source") == "keyword":
            sid = r["symptom_id"]
            merged.setdefault(sid, r)
    # DeepSeek 结果覆盖关键词（中优先级）
    for r in ds_results:
        sid = r["symptom_id"]
        merged[sid] = r  # source 已是 "deepseek"
    # NER 结果覆盖所有（最高优先级）
    for r in existing:
        if r.get("source") == "ner":
            sid = r["symptom_id"]
            merged[sid] = r
    return list(merged.values())


def extract_symptoms(text: str, db: Session) -> list[dict]:
    """
    统一症状提取入口 — NER + 关键词 双引擎 + DeepSeek 保底。
    NER 模型精度高但召回偏低（训练数据有限），关键词召回全面但呆板。
    两者合并去重后，若结果仍不足，触发 DeepSeek 自然语言症状识别。

    NOTE: NER 模型现可提取 BODY/DRUG/TIME 实体类型，但目前仅 SYMPTOM
    实体用于症状-字典匹配（map_to_symptom_dict），BODY/DRUG/TIME 实体
    以原样返回（含 type 字段），可供后续扩展使用。
    """
    bert_results = extract_bert(text)

    # 关键词匹配作为补充
    kw_results = match_keywords(text, db)

    # 合并去重：以 symptom_id 为键，NER 优先
    merged: dict[int, dict] = {}
    for r in kw_results:
        sid = r["symptom_id"]
        merged.setdefault(sid, r)
        merged[sid]["source"] = "keyword"
    for r in bert_results:
        sid = r["symptom_id"]
        merged[sid] = r
        merged[sid]["source"] = "ner"

    results = list(merged.values())

    # 判断是否需要 DeepSeek 保底
    if _is_extraction_insufficient(results):
        from app.services.deepseek_client import is_available, extract_symptoms_from_text
        if is_available():
            logger.info("症状提取不足(共%d, avg_conf=%.2f), 触发 DeepSeek 保底",
                         len(results),
                         sum(r.get("confidence", 0) for r in results) / max(len(results), 1))
            try:
                ds_results = asyncio.get_event_loop().run_until_complete(
                    extract_symptoms_from_text(text, db)
                )
            except RuntimeError:
                # 在已有事件循环中，创建新任务
                import asyncio as _asyncio
                loop = _asyncio.new_event_loop()
                ds_results = loop.run_until_complete(extract_symptoms_from_text(text, db))
                loop.close()
            if ds_results:
                results = _merge_deepseek_results(results, ds_results)

    if bert_results:
        ner_ids = {r["symptom_id"] for r in bert_results}
        logger.info("症状提取: NER=%d, 关键词=%d, DeepSeek=%d, 合并=%d",
                     len(bert_results), len(kw_results),
                     sum(1 for r in results if r.get("source") == "deepseek"),
                     len(results))
    else:
        logger.info("症状提取: 关键词=%d (NER 不可用), 合并=%d",
                     len(kw_results), len(results))

    return results


async def extract_from_description_async(description: str, db: Session) -> list[dict]:
    """异步版本：NER 模型推理放入线程池 + DeepSeek 保底，避免阻塞事件循环"""
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
    results = list(merged.values())

    # DeepSeek 保底：当前两层不足时触发
    if _is_extraction_insufficient(results):
        from app.services.deepseek_client import is_available, extract_symptoms_from_text
        if is_available():
            logger.info("症状提取不足(共%d, avg_conf=%.2f), 触发 DeepSeek 保底",
                         len(results),
                         sum(r.get("confidence", 0) for r in results) / max(len(results), 1))
            ds_results = await extract_symptoms_from_text(text, db)
            if ds_results:
                results = _merge_deepseek_results(results, ds_results)

    if bert_results:
        logger.info("症状提取: NER=%d, 关键词=%d, DeepSeek=%d, 合并=%d",
                     len(bert_results), len(kw_results),
                     sum(1 for r in results if r.get("source") == "deepseek"),
                     len(results))
    else:
        logger.info("症状提取: 关键词=%d (NER 不可用), 合并=%d",
                     len(kw_results), len(results))
    return results


def extract_from_description(description: str, db: Session) -> list[dict]:
    """同步版本（向后兼容）：直接从描述文本提取症状"""
    if not description or not description.strip():
        return []
    return extract_symptoms(description.strip(), db)
