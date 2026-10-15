"""Baseline 학습: configs/dataset.yaml (03_build_split 이 만든 train · val) 로 학습 -> models/baseline/baseline_best.pt

학습 조건(epochs 등)은 src/project_config.py 의 BASELINE_CONFIG 한 곳에서 바꾼다.

학습 조건 문서용 정보는 reports/baseline_run_info.json 에 남긴다.

    python scripts/08_train_baseline.py
    python scripts/08_train_baseline.py --epochs 2   # 동작 확인용
"""
import argparse
import hashlib
import json
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import torch  # noqa: E402
import ultralytics  # noqa: E402
import yaml  # noqa: E402

from src.project_config import (  # noqa: E402
    BASELINE_BEST,
    BASELINE_CONFIG,
    BASELINE_RUN_NAME,
    DATASET_VERSION,
    DATASET_YAML,
    MANIFEST_DIR,
    REPORT_DIR,
    RUNS_DIR,
)
from src.train_detector import train_detector  # noqa: E402


def file_version(path):
    """manifest 버전 = 행 수 + md5 앞 8자리"""
    if not path.exists():
        return "없음"
    data = path.read_bytes()
    rows = data.count(b"\n") - 1  # 헤더 제외
    return f"{path.name} rows={rows} md5={hashlib.md5(data).hexdigest()[:8]}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=BASELINE_CONFIG["epochs"])
    parser.add_argument("--name", default=BASELINE_RUN_NAME)
    args = parser.parse_args()

    cfg = dict(BASELINE_CONFIG, epochs=args.epochs)
    start = datetime.now()
    run_dir = train_detector(
        model_name=cfg["model_name"],
        data_yaml=DATASET_YAML,
        epochs=cfg["epochs"],
        imgsz=cfg["imgsz"],
        batch=cfg["batch"],
        seed=cfg["seed"],
        project=RUNS_DIR,
        name=args.name,
    )
    end = datetime.now()

    best = run_dir / "weights" / "best.pt"
    assert best.exists(), f"best.pt 가 없습니다: {best}"
    BASELINE_BEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, BASELINE_BEST)
    print(f"best.pt -> {BASELINE_BEST.relative_to(PROJECT_ROOT)}")

    train_args = yaml.safe_load((run_dir / "args.yaml").read_text(encoding="utf-8"))
    info = {
        "model": cfg["model_name"],
        "run_name": args.name,
        "run_dir": str(run_dir.relative_to(PROJECT_ROOT)),
        "best_weight": str(BASELINE_BEST.relative_to(PROJECT_ROOT)),
        "dataset_version": DATASET_VERSION,
        "dataset_yaml": str(DATASET_YAML.relative_to(PROJECT_ROOT)),
        "train_manifest": file_version(MANIFEST_DIR / "train.csv"),
        "val_manifest": file_version(MANIFEST_DIR / "val.csv"),
        "epochs": cfg["epochs"],
        "batch": cfg["batch"],
        "imgsz": cfg["imgsz"],
        "seed": cfg["seed"],
        "optimizer": train_args.get("optimizer"),
        "lr0": train_args.get("lr0"),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "python": platform.python_version(),
        "torch": torch.__version__,
        "ultralytics": ultralytics.__version__,
        "start_time": start.isoformat(timespec="seconds"),
        "end_time": end.isoformat(timespec="seconds"),
        "duration_min": round((end - start).total_seconds() / 60, 1),
        "test_bridge_used": False,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / "baseline_run_info.json"
    out.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"학습 정보 -> {out.relative_to(PROJECT_ROOT)}")
    for k, v in info.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
