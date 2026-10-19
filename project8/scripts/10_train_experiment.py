"""개선 실험 학습: Baseline 조건에서 변수 1개만 바꿔 실험별로 따로 학습한다.

실험 조건은 src/experiment_runner.py 의 EXPERIMENTS 에 있다.
    EXP001 = imgsz 640 -> 960        (모델은 yolo11n 그대로)
    EXP002 = yolo11n -> yolo11s      (imgsz 는 640 그대로)
    EXP003 = imgsz 640 -> 1280
    EXP004 = [기준 EXP001] 색 증강 약하게 (hsv_s 0.7 -> 0.3, hsv_v 0.4 -> 0.2)
두 실험을 합친 조건(960 + s)은 만들지 않는다.

실험마다 결과가 따로 저장된다 (서로 덮어쓰지 않음):
    runs/exp001/                       runs/exp002/
    models/improved/exp001_best.pt     models/improved/exp002_best.pt
    reports/exp001_run_info.json       reports/exp002_run_info.json

이미 결과가 있는 실험은 건너뛴다 (실수로 덮어쓰기 방지). 정말 다시 학습하려면 --overwrite.

    python scripts/10_train_experiment.py                      # exp001 -> exp002 순서로 둘 다
    python scripts/10_train_experiment.py --exp exp002         # 하나만
    python scripts/10_train_experiment.py --epochs 1           # 동작 확인 (runs/<exp>_check, 정식 저장 안 함)
    python scripts/10_train_experiment.py --exp exp001 --overwrite   # 다시 학습
"""
import argparse
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

from src.experiment_runner import (  # noqa: E402
    AUG_DEFAULTS,
    EXPERIMENTS,
    build_config,
    changed_text,
    check_same_data_as_baseline,
    manifest_version,
    weight_path,
)
from src.project_config import (  # noqa: E402
    DATASET_VERSION,
    DATASET_YAML,
    MANIFEST_DIR,
    REPORT_DIR,
    RUNS_DIR,
)
from src.train_detector import train_detector  # noqa: E402


def already_done(exp_id):
    """이미 정식 학습 결과가 있으면 그 경로들을 돌려준다 (없으면 빈 리스트)"""
    paths = [RUNS_DIR / exp_id, weight_path(exp_id), REPORT_DIR / f"{exp_id}_run_info.json"]
    return [p for p in paths if p.exists()]


def train_one(exp_id, epochs=None, overwrite=False):
    """실험 하나 학습. 결과는 exp_id 이름의 폴더 · 파일에만 저장한다."""
    cfg, _ = build_config(exp_id)
    is_check = epochs is not None
    if is_check:
        cfg["epochs"] = epochs
    run_name = f"{exp_id}_check" if is_check else exp_id

    print("=" * 60)
    print(f"[{exp_id}] 변경: {changed_text(exp_id)}")
    print(f"[{exp_id}] 조건: {cfg}")

    # 덮어쓰기 방지 (동작 확인 모드는 _check 폴더라 정식 결과와 안 겹침)
    if not is_check:
        done = already_done(exp_id)
        if done and not overwrite:
            print(f"[{exp_id}] 이미 결과가 있어서 건너뜀 (다시 하려면 --overwrite):")
            for p in done:
                print(f"    {p.relative_to(PROJECT_ROOT)}")
            return "skip"
        if done and overwrite and (RUNS_DIR / exp_id).exists():
            shutil.rmtree(RUNS_DIR / exp_id)  # 이전 epoch 기록이 섞이지 않게 비우고 시작
            print(f"[{exp_id}] --overwrite: 이전 runs/{exp_id} 삭제 후 다시 학습")
    else:
        print(f"[{exp_id}] 동작 확인 모드 (epochs={epochs}) → runs/{run_name}, 정식 Weight 저장 안 함")

    # 학습 (Baseline 과 같은 train_detector, train/val 만 사용)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    start = datetime.now()
    run_dir = train_detector(
        model_name=cfg["model_name"],
        data_yaml=DATASET_YAML,
        epochs=cfg["epochs"],
        imgsz=cfg["imgsz"],
        batch=cfg["batch"],
        seed=cfg["seed"],
        patience=cfg["patience"],
        project=RUNS_DIR,
        name=run_name,
        **{k: cfg[k] for k in AUG_DEFAULTS},  # 색 증강 (exp004 외에는 기본값 그대로)
    )
    end = datetime.now()

    best = run_dir / "weights" / "best.pt"
    assert best.exists(), f"best.pt 가 없습니다: {best}"
    if is_check:
        print(f"[{exp_id}] 동작 확인 끝: {best.relative_to(PROJECT_ROOT)} (복사 안 함)")
        return "check"

    # best.pt -> models/improved/<exp>_best.pt
    dst = weight_path(exp_id)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, dst)
    print(f"[{exp_id}] best.pt -> {dst.relative_to(PROJECT_ROOT)}")

    # 학습 조건 기록 (baseline_run_info.json 과 같은 형식 + 변경 정보)
    train_args = yaml.safe_load((run_dir / "args.yaml").read_text(encoding="utf-8"))
    info = {
        "experiment_id": exp_id,
        "changed_variable": changed_text(exp_id),
        "reason": EXPERIMENTS[exp_id]["reason"],
        "model": cfg["model_name"],
        "run_name": run_name,
        "run_dir": str(run_dir.relative_to(PROJECT_ROOT)),
        "best_weight": str(dst.relative_to(PROJECT_ROOT)),
        "dataset_version": DATASET_VERSION,
        "dataset_yaml": str(DATASET_YAML.relative_to(PROJECT_ROOT)),
        "train_manifest": manifest_version(MANIFEST_DIR / "train.csv"),
        "val_manifest": manifest_version(MANIFEST_DIR / "val.csv"),
        "epochs": cfg["epochs"],
        "batch": cfg["batch"],
        "imgsz": cfg["imgsz"],
        "seed": cfg["seed"],
        "patience": cfg["patience"],
        "base": EXPERIMENTS[exp_id].get("base", "baseline_v1"),
        **{k: train_args.get(k) for k in AUG_DEFAULTS},
        "optimizer": train_args.get("optimizer"),
        "lr0": train_args.get("lr0"),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "peak_gpu_memory_gb": round(torch.cuda.max_memory_reserved() / 1024**3, 2) if torch.cuda.is_available() else None,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "ultralytics": ultralytics.__version__,
        "start_time": start.isoformat(timespec="seconds"),
        "end_time": end.isoformat(timespec="seconds"),
        "duration_min": round((end - start).total_seconds() / 60, 1),
        "test_bridge_used": False,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"{exp_id}_run_info.json"
    out.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{exp_id}] 학습 정보 -> {out.relative_to(PROJECT_ROOT)} ({info['duration_min']}분)")
    return "done"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", default="all", choices=["all", *EXPERIMENTS])
    parser.add_argument("--epochs", type=int, default=None, help="동작 확인용으로만 사용")
    parser.add_argument("--overwrite", action="store_true", help="이미 있는 정식 결과를 지우고 다시 학습")
    args = parser.parse_args()

    # Baseline 과 같은 데이터인지 먼저 확인 (다르면 여기서 멈춤)
    check_same_data_as_baseline()

    exp_ids = list(EXPERIMENTS) if args.exp == "all" else [args.exp]
    results = {}
    for exp_id in exp_ids:
        results[exp_id] = train_one(exp_id, epochs=args.epochs, overwrite=args.overwrite)

    print("=" * 60)
    for exp_id, state in results.items():
        print(f"  {exp_id}: {state}")


if __name__ == "__main__":
    main()
