"""project8 공통 경로 · 설정 (scripts 는 모두 여기서 import)"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 폴더
DATA_DIR = PROJECT_ROOT / "data"
YOLO_DIR = DATA_DIR / "yolo"                # 02 가 만드는 학습용 (train · val · test)
BRIDGE_DIR = DATA_DIR / "bridge_holdout"    # 02 가 만드는 Bridge Holdout (학습 · 평가 미사용)
SMOKE_DIR = DATA_DIR / "smoke"              # 03 이 만드는 Smoke 용
CONFIG_DIR = PROJECT_ROOT / "configs"
MANIFEST_DIR = PROJECT_ROOT / "manifests"
MODEL_DIR = PROJECT_ROOT / "models"
RUNS_DIR = PROJECT_ROOT / "runs"
REPORT_DIR = PROJECT_ROOT / "reports"
FIGURE_DIR = REPORT_DIR / "figures"

# Dataset YAML
SMOKE_YAML = CONFIG_DIR / "smoke_dataset.yaml"
DATASET_YAML = CONFIG_DIR / "dataset.yaml"

# ============================================================
# 데이터 위치 설정 (data 받으면 여기만 수정)
# ------------------------------------------------------------
# RAW_DATA_DIR  : 받은 data 를 둔 폴더 (절대경로로 바꿔도 됨)
# SOURCE_SPLITS : split 별 이미지 · TXT 폴더 (RAW_DATA_DIR 기준 상대경로)
# SOURCE_MANIFEST : scene_type · capture_group 등을 가져올 CSV (없으면 None)
#                   image_name 열(또는 relative_path 의 파일명) 으로 매칭
# ============================================================
RAW_DATA_DIR = DATA_DIR / "raw"
SOURCE_SPLITS = {
    "train": {"images": "train/images", "labels": "train/labels"},
    "val": {"images": "validation/images", "labels": "validation/labels"},
    "test": {"images": "test/images", "labels": "test/labels"},
    "bridge_holdout": {"images": "bridge_holdout/images", "labels": "bridge_holdout/labels"},
}
SOURCE_MANIFEST = None
DATASET_VERSION = "kimchi_v1"
# ============================================================

# 교과 7 Class 번호 그대로 사용 (번호 변경 금지)
CLASS_NAMES = {
    0: "leaf_paper",
    1: "plastic_stone_metal",
    2: "branch",
    3: "insect",
    4: "rubber_glove_unused",
    5: "disease_browning",
    6: "green_onion_pepper",
}

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

# Baseline 학습 조건 (smoke 는 epochs 만 줄여서 사용)
BASELINE_CONFIG = {
    "model_name": "yolo11n.pt",
    "epochs": 2,
    "imgsz": 640,
    "batch": 8,
    "seed": 42,
}
BASELINE_RUN_NAME = "baseline_v1"
BASELINE_BEST = MODEL_DIR / "baseline" / "baseline_best.pt"

# 예측 · 평가 기준
PRED_CONF = 0.25
MATCH_IOU = 0.5
