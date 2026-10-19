"""project8 공통 경로 · 설정 (scripts 는 모두 여기서 import)"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 폴더
DATA_DIR = PROJECT_ROOT / "data"
YOLO_DIR = DATA_DIR / "yolo"                # 03_build_split 이 만드는 학습용 (train · val · test)
BRIDGE_DIR = DATA_DIR / "bridge_holdout"    # 03_build_split 이 만드는 Bridge Holdout (학습 · 평가 미사용)
SMOKE_DIR = DATA_DIR / "smoke"              # 05_smoke_train 이 만드는 Smoke 용
CONFIG_DIR = PROJECT_ROOT / "configs"
MANIFEST_DIR = PROJECT_ROOT / "manifests"
MODEL_DIR = PROJECT_ROOT / "models"
RUNS_DIR = PROJECT_ROOT / "runs"
REPORT_DIR = PROJECT_ROOT / "reports"
FIGURE_DIR = REPORT_DIR / "figures"

# Dataset YAML
SMOKE_YAML = CONFIG_DIR / "smoke_dataset.yaml"
DATASET_YAML = CONFIG_DIR / "dataset.yaml"

# 03_build_split.py 입력 (교과 7 FINAL 900장 · 원본, 건드리지 않음)
FINAL_DIR = DATA_DIR / "final"
DATASET_VERSION = "kimchi_v1"

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

# Baseline 학습 조건 (팀 계획 · 07_evaluate_baseline.py 의 CONFIG 와 같게 유지)
#   patience: val 성능(fitness)이 이 epoch 수 동안 좋아지지 않으면 학습을 일찍 멈춤 (Early Stopping)
BASELINE_CONFIG = {
    "model_name": "yolo11n.pt",
    "epochs": 70,
    "imgsz": 640,
    "batch": 16,
    "patience": 30,
    "seed": 42,
}

# Smoke 조건: 짧게 돌리면서 960 · batch 16 의 GPU 메모리를 미리 잰다 (나중 960 실험 대비)
SMOKE_CONFIG = {
    "epochs": 3,
    "imgsz": 1280,
    "batch": 4,
}
BASELINE_RUN_NAME = "baseline_v1"
BASELINE_BEST = MODEL_DIR / "baseline" / "baseline_best.pt"

# 예측 · 평가 기준
PRED_CONF = 0.25
MATCH_IOU = 0.5
