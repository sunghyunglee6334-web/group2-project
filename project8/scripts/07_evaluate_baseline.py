"""Baseline 평가: models/baseline/baseline_best.pt 를 Validation 으로 평가

Test (Frozen) · Bridge 는 여기서 쓰지 않는다.
    reports/baseline_metrics.csv          전체 지표
    reports/baseline_class_metrics.csv    Class 별 지표
    reports/figures/baseline_results.png · baseline_confusion_matrix.png

    python scripts/07_evaluate_baseline.py
"""
import csv
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluate_detector import evaluate_detector  # noqa: E402
from src.project_config import (  # noqa: E402
    BASELINE_BEST,
    BASELINE_CONFIG,
    BASELINE_RUN_NAME,
    DATASET_VERSION,
    DATASET_YAML,
    FIGURE_DIR,
    REPORT_DIR,
    RUNS_DIR,
)

SPLIT = "val"


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def copy_figure(src, dst):
    if src.exists():
        shutil.copy2(src, dst)
        print(f"그래프 -> {dst.relative_to(PROJECT_ROOT)}")
    else:
        print(f"주의: {src} 없음")


def main():
    overall, per_class, save_dir = evaluate_detector(
        weights=BASELINE_BEST,
        data_yaml=DATASET_YAML,
        split=SPLIT,
        imgsz=BASELINE_CONFIG["imgsz"],
        batch=BASELINE_CONFIG["batch"],
        project=RUNS_DIR / "val",
        name=BASELINE_RUN_NAME,
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    row = {"model": BASELINE_RUN_NAME, "dataset_version": DATASET_VERSION, "split": SPLIT, **overall}
    write_csv(REPORT_DIR / "baseline_metrics.csv", [row])
    if per_class:
        write_csv(REPORT_DIR / "baseline_class_metrics.csv", per_class)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    copy_figure(RUNS_DIR / BASELINE_RUN_NAME / "results.png", FIGURE_DIR / "baseline_results.png")
    copy_figure(save_dir / "confusion_matrix.png", FIGURE_DIR / "baseline_confusion_matrix.png")

    print(f"\n{BASELINE_RUN_NAME} · {SPLIT}: {overall}")
    for c in per_class:
        print(f"  {c['class_id']} {c['class_name']:<22} P {c['precision']:.3f}  R {c['recall']:.3f}  "
              f"mAP50 {c['map50']:.3f}  mAP50-95 {c['map50_95']:.3f}")


if __name__ == "__main__":
    main()
