"""Smoke Test: 작은 데이터로 End-to-End 가 도는지 확인 (03_build_split.py 를 COPY_IMAGES = True 로 실행한 다음)

  1단계  data/yolo 의 train · val 에서 무작위(seed 고정) 일부만 data/smoke 로 복사 + configs/smoke_dataset.yaml
         (test · bridge 는 읽지 않는다)
  2단계  3 epoch 학습 → runs/<RUN_NAME>/weights/best.pt 확인 → Val 1장 예측 (runs/predict/<RUN_NAME>)

    python scripts/05_smoke_train.py
"""
import os
import random
import shutil
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO  # noqa: E402

from src.dataset_check import list_images  # noqa: E402
from src.project_config import (  # noqa: E402
    BASELINE_CONFIG,
    CLASS_NAMES,
    PRED_CONF,
    RUNS_DIR,
    SMOKE_DIR,
    SMOKE_YAML,
    YOLO_DIR,
)
from src.train_detector import train_detector  # noqa: E402

N_TRAIN = 30
N_VAL = 8
RUN_NAME = "smoke_v1"
SMOKE_EPOCHS = 3


# ---------------------------------------------------------------- 1단계: Smoke Dataset
def copy_split(split, n):
    img_dir = YOLO_DIR / "images" / split
    lbl_dir = YOLO_DIR / "labels" / split
    if not img_dir.is_dir() or not lbl_dir.is_dir():
        print(f"{img_dir} 가 없습니다. scripts/03_build_split.py 를 COPY_IMAGES = True 로 먼저 실행하세요.")
        raise SystemExit(1)

    all_images = list_images(img_dir)
    if len(all_images) < n:
        print(f"{img_dir} 이미지가 {len(all_images)}장뿐입니다 ({n}장 필요)")
        raise SystemExit(1)
    # 이름순 앞쪽은 같은 촬영 묶음에 몰림 (예: val 앞 8장 = 정상 김치 T02 → 박스 0개 → mAP 0)
    # → seed 고정 무작위로 뽑아 여러 묶음이 섞이게 한다 (다시 돌려도 같은 사진)
    images = sorted(random.Random(BASELINE_CONFIG["seed"]).sample(all_images, n))

    out_img = SMOKE_DIR / "images" / split
    out_lbl = SMOKE_DIR / "labels" / split
    out_img.mkdir(parents=True)
    out_lbl.mkdir(parents=True)
    for img in images:
        lbl = lbl_dir / f"{img.stem}.txt"
        if not lbl.exists():
            print(f"{img.name} 짝 TXT 없음 ({lbl_dir})")
            raise SystemExit(1)
        shutil.copy2(img, out_img / img.name)
        shutil.copy2(lbl, out_lbl / lbl.name)
    n_box = sum(1 for img in images if (lbl_dir / f"{img.stem}.txt").stat().st_size > 0)
    print(f"[{split}] {len(images)}쌍 -> {out_img.relative_to(PROJECT_ROOT)} (박스 있는 사진 {n_box}장 · 배경 {len(images) - n_box}장)")
    return len(images)


def write_smoke_yaml():
    rel = Path(os.path.relpath(SMOKE_DIR, SMOKE_YAML.parent)).as_posix()   # ../data/smoke (PC 마다 같음)
    data = {
        "train": f"{rel}/images/train",
        "val": f"{rel}/images/val",
        "names": CLASS_NAMES,
    }
    SMOKE_YAML.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_YAML.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"YAML -> {SMOKE_YAML.relative_to(PROJECT_ROOT)}")


def make_smoke_dataset():
    # data/smoke 는 이 스크립트가 만드는 파생 폴더라 매번 새로 만든다
    if SMOKE_DIR.exists():
        shutil.rmtree(SMOKE_DIR)
    n_train = copy_split("train", N_TRAIN)
    n_val = copy_split("val", N_VAL)
    write_smoke_yaml()
    print(f"Smoke Dataset: Train {n_train} / Val {n_val}")


# ---------------------------------------------------------------- 2단계: 학습 · 1장 예측
def smoke_train():
    cfg = BASELINE_CONFIG
    run_dir = train_detector(
        model_name=cfg["model_name"],
        data_yaml=SMOKE_YAML,
        epochs=SMOKE_EPOCHS,
        imgsz=cfg["imgsz"],
        batch=cfg["batch"],
        seed=cfg["seed"],
        project=RUNS_DIR,
        name=RUN_NAME,
    )

    best = run_dir / "weights" / "best.pt"
    assert best.exists(), f"best.pt 가 없습니다: {best}"
    print(f"best.pt 확인: {best}")

    first = list_images(SMOKE_DIR / "images" / "val")[0]
    results = YOLO(str(best)).predict(
        source=str(first),
        conf=PRED_CONF,
        save=True,
        project=str(RUNS_DIR / "predict"),
        name=RUN_NAME,
        exist_ok=True,
    )

    boxes = results[0].boxes
    print(f"예측: {first.name} -> Box {len(boxes)}개 (conf >= {PRED_CONF})")
    for cls, conf in zip(boxes.cls.tolist(), boxes.conf.tolist()):
        print(f"  class {int(cls)} {CLASS_NAMES[int(cls)]}  conf {conf:.3f}")
    print(f"저장 위치: {RUNS_DIR / 'predict' / RUN_NAME}")


def main():
    print("[1단계] Smoke Dataset 만들기")
    make_smoke_dataset()
    print("\n[2단계] Smoke 학습 · 1장 예측")
    smoke_train()


if __name__ == "__main__":
    main()
