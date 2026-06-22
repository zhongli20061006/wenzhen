import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(MODEL_DIR, "data")
OUTPUT_DIR = os.path.join(MODEL_DIR, "output", "symptom_ner")
BASE_MODEL = "shibing624/bert4ner-base-chinese"
LABEL_LIST = ["O", "B-SYMPTOM", "I-SYMPTOM"]
MAX_LENGTH = 128
BATCH_SIZE = 32
EPOCHS = 15
LR = 3e-5

# Checkpoint 880 路径（从已有微调模型继续训练，而非从基座重新开始）
CHECKPOINT_880 = os.path.join(OUTPUT_DIR, "checkpoint-880")
RESUME_FROM = CHECKPOINT_880 if os.path.exists(CHECKPOINT_880) else BASE_MODEL


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def bio_annotate(text: str, entities: list[dict]) -> list[str]:
    labels = ["O"] * len(text)
    for e in entities:
        s, e_idx = e["start_idx"], e["end_idx"]
        if s < len(labels):
            labels[s] = "B-SYMPTOM"
            for i in range(s + 1, min(e_idx + 1, len(labels))):
                labels[i] = "I-SYMPTOM"
    return labels


class SymptomDataset:
    def __init__(self, samples, tokenizer):
        self.encodings = []
        self.labels = []

        for sample in samples:
            bio = bio_annotate(sample["text"], sample["entities"])
            tokens = tokenizer(
                list(sample["text"]),
                is_split_into_words=True,
                truncation=True,
                max_length=MAX_LENGTH,
                padding="max_length",
                return_tensors="pt",
            )
            word_ids = tokens.word_ids()
            aligned_labels = []
            prev_word = None
            for word_id in word_ids:
                if word_id is None:
                    aligned_labels.append(-100)
                elif word_id != prev_word:
                    aligned_labels.append(LABEL_LIST.index(bio[word_id]))
                else:
                    aligned_labels.append(LABEL_LIST.index(bio[word_id]))
                prev_word = word_id

            self.encodings.append({
                "input_ids": tokens["input_ids"].squeeze(0),
                "attention_mask": tokens["attention_mask"].squeeze(0),
                "labels": __import__("torch").tensor(aligned_labels),
            })

    def __len__(self):
        return len(self.encodings)

    def __getitem__(self, idx):
        return self.encodings[idx]


def train():
    from transformers import (
        AutoTokenizer, AutoModelForTokenClassification,
        TrainingArguments, Trainer, DataCollatorForTokenClassification,
        EarlyStoppingCallback,
    )
    from datasets import Dataset
    from seqeval.metrics import classification_report as seq_report
    import numpy as np
    import torch

    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True, local_files_only=True)

    train_raw = load_json(os.path.join(DATA_DIR, "train.json"))
    dev_raw = load_json(os.path.join(DATA_DIR, "dev.json"))

    def to_dataset(samples):
        texts, bio_tags = [], []
        for s in samples:
            bio = bio_annotate(s["text"], s["entities"])
            texts.append(list(s["text"]))
            bio_tags.append(bio)
        return Dataset.from_dict({"tokens": texts, "tags": bio_tags})

    train_ds = to_dataset(train_raw)
    dev_ds = to_dataset(dev_raw)

    id2label = {i: l for i, l in enumerate(LABEL_LIST)}
    label2id = {l: i for i, l in enumerate(LABEL_LIST)}

    # Count label distribution for class_weight
    o_count = sum(1 for s in train_raw for l in bio_annotate(s["text"], s["entities"]) if l == "O")
    b_count = sum(1 for s in train_raw for l in bio_annotate(s["text"], s["entities"]) if l == "B-SYMPTOM")
    i_count = sum(1 for s in train_raw for l in bio_annotate(s["text"], s["entities"]) if l == "I-SYMPTOM")
    total = o_count + b_count + i_count
    print(f"Label分布: O={o_count}({o_count/total:.1%}) B={b_count}({b_count/total:.1%}) I={i_count}({i_count/total:.1%})")

    print(f"加载模型: {RESUME_FROM}")
    model = AutoModelForTokenClassification.from_pretrained(
        RESUME_FROM,
        num_labels=len(LABEL_LIST),
        id2label=id2label,
        label2id=label2id,
        trust_remote_code=True,
        ignore_mismatched_sizes=True,
        local_files_only=True,
    )

    def tokenize_and_align_labels(examples):
        tokenized = tokenizer(
            examples["tokens"],
            is_split_into_words=True,
            truncation=True,
            max_length=MAX_LENGTH,
            padding="max_length",
        )
        aligned_labels = []
        for i, labels in enumerate(examples["tags"]):
            word_ids = tokenized.word_ids(batch_index=i)
            prev_word = None
            label_ids = []
            for word_id in word_ids:
                if word_id is None:
                    label_ids.append(-100)
                elif word_id != prev_word:
                    label_ids.append(label2id[labels[word_id]])
                else:
                    label_ids.append(label2id[labels[word_id]])
                prev_word = word_id
            aligned_labels.append(label_ids)
        tokenized["labels"] = aligned_labels
        return tokenized

    train_tokenized = train_ds.map(tokenize_and_align_labels, batched=True)
    dev_tokenized = dev_ds.map(tokenize_and_align_labels, batched=True)

    def compute_metrics(p):
        predictions, labels = p
        predictions = np.argmax(predictions, axis=2)
        true_predictions = [
            [LABEL_LIST[p] for (p, l) in zip(pred, label) if l != -100]
            for pred, label in zip(predictions, labels)
        ]
        true_labels = [
            [LABEL_LIST[l] for (p, l) in zip(pred, label) if l != -100]
            for pred, label in zip(predictions, labels)
        ]
        report = seq_report(true_labels, true_predictions, output_dict=True, zero_division=0)
        return {"f1": report["macro avg"]["f1-score"], "precision": report["macro avg"]["precision"], "recall": report["macro avg"]["recall"]}

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        learning_rate=LR,
        warmup_ratio=0.05,
        weight_decay=0.01,
        logging_steps=30,
        eval_strategy="steps",
        eval_steps=40,
        save_strategy="steps",
        save_steps=40,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        fp16=False,
        dataloader_num_workers=0,
        save_total_limit=3,
    )

    early_stop = EarlyStoppingCallback(early_stopping_patience=5, early_stopping_threshold=0.001)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=dev_tokenized,
        processing_class=tokenizer,
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[early_stop],
    )

    print(f"开始训练: {len(train_raw)} train / {len(dev_raw)} dev")
    trainer.train()

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # Dev eval
    metrics = trainer.evaluate()
    print(f"\n===== Dev集评估 =====")
    print(f"  F1={metrics.get('eval_f1', 0):.4f}, P={metrics.get('eval_precision', 0):.4f}, R={metrics.get('eval_recall', 0):.4f}")

    # CMeEE cross-distribution eval
    cmee_raw_dir = os.path.join(MODEL_DIR, "data", "cmee_raw")
    cmee_dev_path = os.path.join(cmee_raw_dir, "CMeEE-V2_dev.json")
    if os.path.exists(cmee_dev_path):
        print(f"\n===== CMeEE跨分布评估 =====")
        cmee_data = load_json(cmee_dev_path)
        cmee_sym = [{"text": item["text"], "entities": [e for e in item.get("entities", []) if e["type"] in ("sym", "dis")]} for item in cmee_data[:1000]]
        cmee_sym = [s for s in cmee_sym if s["entities"]]
        cmee_ds = to_dataset(cmee_sym)
        cmee_tokenized = cmee_ds.map(tokenize_and_align_labels, batched=True)
        cmee_tokenized.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])
        result = trainer.predict(cmee_tokenized)
        preds = np.argmax(result.predictions, axis=2)
        true_preds = [[LABEL_LIST[p] for (p, l) in zip(pr, la) if l != -100] for pr, la in zip(preds, result.label_ids)]
        true_labs = [[LABEL_LIST[l] for (p, l) in zip(pr, la) if l != -100] for pr, la in zip(preds, result.label_ids)]
        cmee_report = seq_report(true_labs, true_preds, output_dict=True, zero_division=0)
        print(f"  样本数: {len(cmee_sym)}")
        print(f"  F1={cmee_report['macro avg']['f1-score']:.4f}, P={cmee_report['macro avg']['precision']:.4f}, R={cmee_report['macro avg']['recall']:.4f}")

    print(f"模型已保存: {OUTPUT_DIR}")


if __name__ == "__main__":
    train()
