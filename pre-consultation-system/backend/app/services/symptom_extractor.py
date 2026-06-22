import os
from sqlalchemy.orm import Session
from app.models.symptom_dict import SymptomDict
from app.models.symptom_synonym import SymptomSynonym
from app.logger import logger

_tokenizer = None
_model = None
_ner_labels = None


def _load_bert():
    global _tokenizer, _model, _ner_labels
    if _model is not None:
        return True
    try:
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        import torch
        model_name = "shibing624/bert4ner-base-chinese"
        logger.info("加载 BERT NER 模型 %s (hf-mirror) ...", model_name)
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForTokenClassification.from_pretrained(model_name)
        if hasattr(_model, "config") and hasattr(_model.config, "id2label"):
            _ner_labels = {v: k for k, v in _model.config.label2id.items()}
        logger.info("BERT NER 模型加载完成")
        return True
    except Exception as e:
        logger.warning("BERT 模型加载失败: %s", e)
        return False


def _bert_predict(text: str) -> list[tuple[str, str]]:
    """Run BERT NER inference, return list of (entity_text, entity_label)."""
    import torch
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        outputs = _model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=-1).squeeze().tolist()
    tokens = _tokenizer.convert_ids_to_tokens(inputs["input_ids"].squeeze().tolist())

    entities = []
    current_entity = []
    current_label = None

    for token, pred_id in zip(tokens, predictions):
        if token in ("[CLS]", "[SEP]", "[PAD]"):
            continue
        label = _ner_labels.get(pred_id, "O") if _ner_labels else "O"

        if label.startswith("B-"):
            if current_entity:
                entities.append(("".join(current_entity), current_label))
            current_entity = [token.lstrip("##")]
            current_label = label[2:]
        elif label.startswith("I-") and current_entity:
            current_entity.append(token.lstrip("##"))
        else:
            if current_entity:
                entities.append(("".join(current_entity), current_label))
                current_entity = []
                current_label = None
    if current_entity:
        entities.append(("".join(current_entity), current_label))

    return entities


def extract_bert(text: str) -> list[dict]:
    """
    BERT NER 提取症状实体。
    仅返回 NER 模型结果（可能为空），不回退关键词——回退逻辑由上层 extraction_service 合并处理。
    """
    db = None
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        from model.predict_ner import predict_entities, map_to_symptom_dict
        entities = predict_entities(text)
        if entities:
            results = map_to_symptom_dict(entities, db)
            if results:
                logger.debug("NER 模型提取: %d 个症状实体", len(results))
                return results
        return []  # NER 无结果，交由上层合并关键词
    except Exception as e:
        logger.debug("NER 模型不可用(%s)，交由上层合并关键词", e)
        return []
    finally:
        if db:
            db.close()


def _fuzzy_contains(query: str, text: str) -> bool:
    """检查 query 的所有字符是否按顺序出现在 text 中（允许间隔）。
    用于匹配口语化表达如 '胸闷' -> '胸口有点闷'，'嗓子疼' -> '嗓子也疼'。"""
    if len(query) <= 1:
        return query in text
    pos = 0
    for i, ch in enumerate(text):
        if ch == query[pos]:
            pos += 1
            if pos == len(query):
                return True
    return False


def _strip_fillers(text: str) -> str:
    """去除口语填充词，得到更干净的文本用于子串匹配。"""
    fillers = ["有点", "特别", "非常", "很", "也", "还是", "总是", "一直",
               "不太", "比较", "稍微", "略微", "挺", "好"]
    result = text
    for f in fillers:
        result = result.replace(f, "")
    return result


def _match_term(term: str, text: str) -> str | None:
    """三种策略匹配 term：精确子串 > 模糊序匹配 > 去填充词子串。
    返回匹配策略名或 None。"""
    if not term:
        return None
    # 1. 精确子串
    if term in text:
        return "exact"
    # 2. 模糊序匹配（2字及以上）
    if len(term) >= 2 and _fuzzy_contains(term, text):
        return "fuzzy"
    # 3. 去填充词后子串匹配
    stripped = _strip_fillers(text)
    if term in stripped:
        return "stripped"
    if len(term) >= 2 and _fuzzy_contains(term, stripped):
        return "stripped_fuzzy"
    return None


def match_keywords(text: str, db: Session) -> list[dict]:
    """
    关键词/别名匹配提取症状。
    支持精确匹配 + 模糊序匹配（如 '胸闷'→'胸口有点闷'）+ 去口语填充词匹配。
    比 standardize_symptoms 多一层 synonym 表匹配。
    返回 [{symptom_id, symptom_name, match_type, confidence}]。
    """
    results: dict[int, dict] = {}
    symptoms = db.query(SymptomDict).all()
    sym_map = {s.id: s for s in symptoms}

    for sym in symptoms:
        name = sym.name
        match_strategy = _match_term(name, text)
        if match_strategy:
            conf = {"exact": 1.0, "fuzzy": 0.8, "stripped": 0.75, "stripped_fuzzy": 0.65}.get(match_strategy, 0.6)
            results.setdefault(sym.id, {
                "symptom_id": sym.id, "symptom_name": name,
                "match_type": f"name_{match_strategy}", "confidence": conf,
            })
            continue
        if sym.aliases:
            for alias in sym.aliases.split(","):
                alias = alias.strip()
                if not alias:
                    continue
                match_strategy = _match_term(alias, text)
                if match_strategy:
                    conf = {"exact": 0.95, "fuzzy": 0.75, "stripped": 0.7, "stripped_fuzzy": 0.6}.get(match_strategy, 0.55)
                    results.setdefault(sym.id, {
                        "symptom_id": sym.id, "symptom_name": name,
                        "match_type": f"alias_{match_strategy}", "confidence": conf,
                    })
                    break

    synonyms = db.query(SymptomSynonym).all()
    for syn in synonyms:
        if syn.symptom_id in results:
            continue
        match_strategy = _match_term(syn.term, text)
        if match_strategy:
            sym = sym_map.get(syn.symptom_id)
            if sym:
                conf = round(syn.weight, 2) * 0.9 if "exact" not in match_strategy else syn.weight
                results[syn.symptom_id] = {
                    "symptom_id": sym.id, "symptom_name": sym.name,
                    "match_type": f"synonym_{match_strategy}", "confidence": round(conf, 2),
                }

    return list(results.values())
