"""11c_compare_failures.py — Baseline · EXP001~004 의 실패 유형 · 크기별 FN 을 같은 기준으로 비교한다.

실행 (project8 폴더에서, 11b_evaluate_experiment.py 다음에):
    python scripts/11c_compare_failures.py                 # 5개 모델 전부
    python scripts/11c_compare_failures.py --models baseline exp003

입력 : models/baseline/baseline_best.pt, models/improved/exp00N_best.pt
       data/yolo/images/val, data/yolo/labels/val, data/yolo/labels/train (크기 경계 계산용)
출력 : reports/failure_compare.csv        모델별 TP · FP · FN · CLASS · BBOX 개수
       reports/fn_by_size_compare.csv     모델 × Class × 크기별 놓친 비율
       runs/pred_val_cmp/<모델>/labels/   예측 TXT (사진은 저장 안 함 · NDA)

판정은 ④ Evaluation 과 같은 src/failure_analyzer.py (conf ≥ 0.25 · IoU ≥ 0.5 + 같은 Class = TP) 를 그대로 쓴다.
크기 경계는 10_fn_by_size.py 와 같은 방식(긴 변 640px 기준 √넓이, Class마다 1/3)이며,
Split v4-B 의 Train + Val 정답 박스로 계산한다. 모든 모델이 같은 경계를 쓴다.
각 모델은 자기가 학습한 imgsz 로 예측한다. Frozen Test 는 열지 않는다.
"""
import argparse
import importlib.util
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.failure_analyzer import FAILURE_TYPES, analyze_image, count_types  # noqa: E402
from src.label_visualizer import read_yolo_labels  # noqa: E402
from src.project_config import MODEL_DIR, REPORT_DIR, RUNS_DIR  # noqa: E402

# 10_fn_by_size.py 의 size_bin · count_by_size 를 그대로 재사용 (이름이 숫자로 시작해서 import 대신 로드)
_spec = importlib.util.spec_from_file_location("fn_by_size", PROJECT_ROOT / "scripts" / "10_fn_by_size.py")
fn_by_size = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fn_by_size)

YOLO_DIR = PROJECT_ROOT / "data" / "yolo"
IMAGE_DIR = YOLO_DIR / "images" / "val"
LABEL_DIR = YOLO_DIR / "labels" / "val"
BIN_LABEL_DIRS = [YOLO_DIR / "labels" / "train", YOLO_DIR / "labels" / "val"]
BIN_IMAGE_DIRS = [YOLO_DIR / "images" / "train", YOLO_DIR / "images" / "val"]
PRED_ROOT = RUNS_DIR / "pred_val_cmp"
CONF = 0.25
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# (이름, weight, 학습 imgsz)
MODELS = {
    "baseline": (MODEL_DIR / "baseline" / "baseline_best.pt", 640),
    "exp001": (MODEL_DIR / "improved" / "exp001_best.pt", 960),
    "exp002": (MODEL_DIR / "improved" / "exp002_best.pt", 640),
    "exp003": (MODEL_DIR / "improved" / "exp003_best.pt", 1280),
    "exp004": (MODEL_DIR / "improved" / "exp004_best.pt", 1280),
}


def list_images(d):
    return sorted(p for p in Path(d).iterdir() if p.suffix.lower() in IMAGE_EXTS)


def tertile_bins(label_dirs, image_dirs):
    """Class마다 정답 박스 크기(긴 변 640 기준 √넓이)를 1/3씩 나누는 경계 (small 경계, large 경계)"""
    sides = {}
    for ldir, idir in zip(label_dirs, image_dirs):
        for img in list_images(idir):
            W, H = Image.open(img).size
            scale = fn_by_size.TRAIN_PX / max(W, H)
            for g in read_yolo_labels(ldir / f"{img.stem}.txt"):
                sides.setdefault(g[0], []).append(((g[3] * W * scale) * (g[4] * H * scale)) ** 0.5)
    return {c: tuple(np.percentile(v, [100 / 3, 200 / 3])) for c, v in sides.items()}


def predict(name, weight, imgsz, images):
    """예측 TXT 만 저장 (사진 저장 X)"""
    from ultralytics import YOLO

    out = PRED_ROOT / name
    model = YOLO(str(weight))
    for img in images:
        model.predict(str(img), imgsz=imgsz, conf=CONF, save=False, save_txt=True, save_conf=True,
                      project=str(PRED_ROOT), name=name, exist_ok=True, verbose=False)
    return out / "labels"


def type_counts(images, pred_dir):
    total = Counter()
    for img in images:
        total.update(count_types(analyze_image(LABEL_DIR / f"{img.stem}.txt", pred_dir / f"{img.stem}.txt")))
    return {t: total[t] for t in FAILURE_TYPES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    a = ap.parse_args()

    images = list_images(IMAGE_DIR)
    bins = tertile_bins(BIN_LABEL_DIRS, BIN_IMAGE_DIRS)
    print("크기 경계(px, Class별 small < a ≤ medium < b ≤ large):",
          {c: (round(float(lo), 1), round(float(hi), 1)) for c, (lo, hi) in sorted(bins.items())})

    type_rows, size_rows = [], []
    for name in a.models:
        weight, imgsz = MODELS[name]
        if not weight.exists():
            print(f"[{name}] weight 없음 → 건너뜀: {weight.relative_to(PROJECT_ROOT)}")
            continue
        print(f"[{name}] 예측 중 (imgsz {imgsz}, Val {len(images)}장)")
        pred_dir = predict(name, weight, imgsz, images)
        tc = type_counts(images, pred_dir)
        type_rows.append({"model": name, "imgsz": imgsz, **tc})
        df = fn_by_size.count_by_size(images, LABEL_DIR, pred_dir, bins)
        df.insert(0, "model", name)
        size_rows.append(df)

    if not type_rows:
        sys.exit("비교할 모델이 없습니다.")
    t = pd.DataFrame(type_rows)
    s = pd.concat(size_rows, ignore_index=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    t.to_csv(REPORT_DIR / "failure_compare.csv", index=False, encoding="utf-8-sig")
    s.to_csv(REPORT_DIR / "fn_by_size_compare.csv", index=False, encoding="utf-8-sig")

    print(f"\n[실패 유형 개수 · Val {len(images)}장 · conf 0.25 · IoU 0.5]")
    print(t.to_string(index=False))
    print("\n[전체 크기별 놓친 비율]")
    allrows = s[s["class"] == "all"].pivot(index="model", columns="size", values="miss_rate")
    print(allrows.reindex(columns=["small", "medium", "large"]).reindex([r["model"] for r in type_rows]).to_string())
    print("\n저장: reports/failure_compare.csv, reports/fn_by_size_compare.csv")


if __name__ == "__main__":
    main()
