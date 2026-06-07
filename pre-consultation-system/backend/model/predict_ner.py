import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(MODEL_DIR, "output", "symptom_ner")
LABEL_LIST = ["O", "B-SYMPTOM", "I-SYMPTOM"]

_model = None
_tokenizer = None
_loaded = False


def _load_model():
    global _model, _tokenizer, _loaded
    if _loaded:
        return

    try:
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        import torch

        if os.path.exists(OUTPUT_DIR):
            path = OUTPUT_DIR
        else:
            path = "shibing624/bert4ner-base-chinese"

        _tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
        _model = AutoModelForTokenClassification.from_pretrained(
            path, num_labels=len(LABEL_LIST), trust_remote_code=True, ignore_mismatched_sizes=True,
        )
        _model.eval()
        _loaded = True
    except Exception as e:
        print(f"模型加载失败: {e}")
        _loaded = False


def _entity_decode(text: str, prediction_ids: list[int]) -> list[dict]:
    entities = []
    current = []
    for i, pid in enumerate(prediction_ids):
        if i >= len(text):
            break
        label = LABEL_LIST[pid] if pid < len(LABEL_LIST) else "O"
        if label == "B-SYMPTOM":
            if current:
                entities.append({
                    "start": current[0], "end": i - 1,
                    "text": text[current[0]:i],
                })
            current = [i]
        elif label == "I-SYMPTOM" and current:
            current.append(i)
        elif label == "O":
            if current:
                entities.append({
                    "start": current[0], "end": i - 1,
                    "text": text[current[0]:i],
                })
            current = []

    if current:
        entities.append({
            "start": current[0], "end": len(text) - 1,
            "text": text[current[0]:],
        })

    return [e for e in entities if len(e["text"]) >= 2]


def predict_entities(text: str, confidence_threshold: float = 0.5) -> list[dict]:
    import torch
    _load_model()
    if not _loaded:
        return []

    chars = list(text)
    inputs = _tokenizer(
        chars, is_split_into_words=True,
        truncation=True, max_length=128,
        padding="max_length", return_tensors="pt",
    )
    with torch.no_grad():
        outputs = _model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=-1).squeeze().tolist()

    word_ids = inputs.word_ids()
    # Dedup: only first subtoken per word
    unique_predictions = []
    prev_word = None
    for word_id, pred in zip(word_ids, predictions):
        if word_id is None:
            continue
        if word_id != prev_word:
            unique_predictions.append(pred)
        prev_word = word_id

    entities = _entity_decode(text, unique_predictions)

    # Filter by length
    return [e for e in entities if len(e["text"]) >= 2]


def map_to_symptom_dict(entities: list[dict], db):
    from app.models.symptom_dict import SymptomDict
    symptoms = db.query(SymptomDict).all()

    results = []
    for entity in entities:
        text = entity["text"]
        for sym in symptoms:
            if text == sym.name:
                results.append({"symptom_id": sym.id, "symptom_name": sym.name, "match_type": "name", "confidence": 0.9})
                break
            if sym.aliases:
                for alias in sym.aliases.split(","):
                    if alias.strip() == text:
                        results.append({"symptom_id": sym.id, "symptom_name": sym.name, "match_type": "alias", "confidence": 0.85})
                        break
                else:
                    continue
                break
        if text not in {sym.name for sym in symptoms}:
            for sym in symptoms:
                if sym.name and text in sym.name:
                    results.append({"symptom_id": sym.id, "symptom_name": sym.name, "match_type": "partial", "confidence": 0.4})
                    break

    return results
