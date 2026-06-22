import json
import os
import shutil

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(DATA_DIR, "data", "cmee_raw")
MEDDIALOG_DIR = os.path.join(DATA_DIR, "data", "meddialog")
CMEE_REPO = "https://github.com/hs3434/CMeEE-V2.git"

ANNOTATED_PATH = os.path.join(DATA_DIR, "annotated_symptoms.json")


def download_cmee():
    os.makedirs(RAW_DIR, exist_ok=True)

    expected = ["CMeEE-V2_train.json", "CMeEE-V2_dev.json"]
    if all(os.path.exists(os.path.join(RAW_DIR, f)) for f in expected):
        sizes = [os.path.getsize(os.path.join(RAW_DIR, f)) for f in expected]
        if all(s > 100000 for s in sizes):
            print(f"CMeEE-V2 已存在: {RAW_DIR}")
            return

    import subprocess, tempfile

    tmp = os.path.join(tempfile.gettempdir(), "cmee_v2")
    if not os.path.exists(os.path.join(tmp, "CMeEE-V2_train.json")):
        print(f"git clone {CMEE_REPO} ...")
        subprocess.run(
            ["git", "lfs", "install"],
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "clone", CMEE_REPO, tmp, "--depth", "1"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"git clone 失败: {result.stderr}")
            print("请手动执行: git lfs install && git clone https://github.com/hs3434/CMeEE-V2.git")
            return

    for fname in expected:
        src = os.path.join(tmp, fname)
        dst = os.path.join(RAW_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  复制 {fname}: {os.path.getsize(dst) / 1024 / 1024:.1f} MB")
        else:
            print(f"  找不到 {fname}, 请检查 git clone 是否成功")

    print(f"CMeEE-V2 下载完成, 路径: {RAW_DIR}")


def load_cmee_split(name: str) -> list[dict]:
    path = os.path.join(RAW_DIR, f"{name}.json")
    if not os.path.exists(path):
        download_cmee()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_annotated() -> list[dict]:
    if os.path.exists(ANNOTATED_PATH):
        with open(ANNOTATED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            for e in item.get("entities", []):
                if "type" not in e:
                    e["type"] = "sym"
            item["source"] = "annotated"
        return data
    print(f"未找到标注文件: {ANNOTATED_PATH}")
    return []


def download_meddialog(limit: int = 5000):
    os.makedirs(MEDDIALOG_DIR, exist_ok=True)
    output = os.path.join(MEDDIALOG_DIR, "patient_sentences.json")

    if os.path.exists(output) and os.path.getsize(output) > 10000:
        print(f"MedDialog 已下载: {output}")
        return output

    print("正在从 HuggingFace 下载 MedDialog ...")
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    try:
        from datasets import load_dataset
        dataset = load_dataset("shibing624/medical", split="train", streaming=True)
        sentences = []
        for item in dataset:
            if len(sentences) >= limit:
                break
            text = item.get("output", "") or item.get("question", "") or ""
            text = text.strip()
            if len(text) >= 8 and len(text) <= 200:
                sentences.append(text)
        print(f"  提取患者句子: {len(sentences)} 条")

        with open(output, "w", encoding="utf-8") as f:
            json.dump(sentences, f, ensure_ascii=False, indent=2)
        print(f"MedDialog 保存至: {output}")
        return output
    except Exception as e:
        print(f"MedDialog 下载失败: {e}")
        return None


if __name__ == "__main__":
    download_cmee()
    load_annotated()
    download_meddialog()
