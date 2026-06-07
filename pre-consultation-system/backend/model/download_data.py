import json
import os
import zipfile
import io
import urllib.request

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(DATA_DIR, "data", "cmee_raw")
CMEE_V2_REPO = "https://github.com/hs3434/CMeEE-V2/archive/refs/heads/main.zip"


def download_cmee():
    """从 GitHub 镜像拉取 CMeEE-V2 数据集并解压到 data/cmee_raw/"""
    os.makedirs(RAW_DIR, exist_ok=True)

    expected = ["CMeEE-V2_train.json", "CMeEE-V2_dev.json"]
    if all(os.path.exists(os.path.join(RAW_DIR, f)) for f in expected):
        print(f"CMeEE-V2 已存在: {RAW_DIR}")
        return

    print(f"下载 CMeEE-V2: {CMEE_V2_REPO}")
    try:
        resp = urllib.request.urlopen(CMEE_V2_REPO, timeout=120)
        data = resp.read()
    except Exception as e:
        print(f"下载失败: {e}")
        print("请手动将 CMeEE-V2_train.json, CMeEE-V2_dev.json 放入 data/cmee_raw/")
        return

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.namelist():
            basename = os.path.basename(member)
            if basename.endswith(".json"):
                content = zf.read(member)
                out_path = os.path.join(RAW_DIR, basename)
                with open(out_path, "wb") as f:
                    f.write(content)
                print(f"  解压: {basename}")

    print(f"CMeEE-V2 下载完成, 路径: {RAW_DIR}")


def load_cmee_split(name: str) -> list[dict]:
    path = os.path.join(RAW_DIR, f"{name}.json")
    if not os.path.exists(path):
        download_cmee()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    download_cmee()
