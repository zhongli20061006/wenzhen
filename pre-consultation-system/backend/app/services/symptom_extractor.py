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
        _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        _model = AutoModelForTokenClassification.from_pretrained(model_name, trust_remote_code=True)
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
    优先使用微调后的医学 NER 模型，不可用时回退关键词匹配。
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
        return match_keywords(text, db)
    except Exception as e:
        logger.debug("NER 模型不可用(%s), 回退关键词匹配", e)
        if db is None:
            from app.database import SessionLocal
            db = SessionLocal()
        return match_keywords(text, db)
    finally:
        if db:
            db.close()


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
