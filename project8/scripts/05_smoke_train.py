"""Smoke 학습: 3 epoch 로 학습 → best.pt 확인 → Val 1장 예측

    python scripts/05_smoke_train.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO  # noqa: E402

from src.project_config import (  # noqa: E402
    BASELINE_CONFIG,
    CLASS_NAMES,
    IMG_EXTS,
    PRED_CONF,
    RUNS_DIR,
    SMOKE_DIR,
    SMOKE_YAML,
)
from src.train_detector import train_detector  # noqa: E402

RUN_NAME = "smoke_v1"
SMOKE_EPOCHS = 3


def main():
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

    val_images = sorted(p for p in (SMOKE_DIR / "images" / "val").iterdir() if p.suffix.lower() in IMG_EXTS)
    first = val_images[0]
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


if __name__ == "__main__":
    main()
