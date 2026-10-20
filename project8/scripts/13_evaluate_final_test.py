"""13_evaluate_final_test.py — Final Model 을 Frozen Test 로 딱 한 번 평가한다 (가이드 21.2).

실행 (project8 폴더에서, final_model_selection.md 작성 · final_best.pt 복사 다음에):
    python scripts/13_evaluate_final_test.py

입력 : models/final/final_best.pt  (= models/improved/exp003_best.pt 복사본)
       configs/dataset.yaml 의 test (Split v4-B · 75장)
출력 : reports/final_metrics.csv                     전체 P · R · mAP50 · mAP50-95
       reports/final_class_metrics.csv               Class별
       reports/figures/final_test_confusion_matrix.png
       runs/final_test/                              Ultralytics 결과 (사진은 Git 제외)

규칙
  - Final 은 Validation 으로 이미 정했다. Test 결과를 보고 모델 · 설정을 바꾸지 않는다.
  - imgsz 는 Final 이 학습한 값(1280)과 같게 한다.
  - 이미 final_metrics.csv 가 있으면 멈춘다 (실수로 두 번 돌리는 것 방지). 정말 다시 해야 하면 --force.
"""
import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluate_detector import (  # noqa: E402
    evaluate_detector,
    save_metrics_csv,
    summarize_overall,
    summarize_per_class,
)
from src.project_config import DATASET_VERSION, DATASET_YAML, FIGURE_DIR, MODEL_DIR, REPORT_DIR, RUNS_DIR  # noqa: E402

FINAL_WEIGHT = MODEL_DIR / "final" / "final_best.pt"
FINAL_SOURCE = "exp003"          # final_model_selection.md 와 같게
FINAL_MODEL = "yolo11n.pt"
FINAL_IMGSZ = 1280
OUT_METRICS = REPORT_DIR / "final_metrics.csv"
OUT_CLASS = REPORT_DIR / "final_class_metrics.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="이미 결과가 있어도 다시 평가 (사유를 문서에 남길 것)")
    a = ap.parse_args()

    if not FINAL_WEIGHT.exists():
        sys.exit(f"Final weight 가 없습니다: {FINAL_WEIGHT.relative_to(PROJECT_ROOT)}\n"
                 f"  먼저: cp models/improved/{FINAL_SOURCE}_best.pt models/final/final_best.pt")
    if OUT_METRICS.exists() and not a.force:
        sys.exit(f"이미 Frozen Test 결과가 있습니다: {OUT_METRICS.relative_to(PROJECT_ROOT)} (Test 는 한 번만)")

    print(f"Frozen Test 평가: {FINAL_WEIGHT.relative_to(PROJECT_ROOT)} ({FINAL_SOURCE}) · imgsz {FINAL_IMGSZ} · split=test")
    metrics = evaluate_detector(
        str(FINAL_WEIGHT), str(DATASET_YAML),
        split="test", imgsz=FINAL_IMGSZ, allow_test=True,
        project=RUNS_DIR, name="final_test",
    )

    overall = summarize_overall(metrics)
    row = {"model_version": "final", "source": FINAL_SOURCE, "dataset_version": DATASET_VERSION,
           "split": "test", "model": FINAL_MODEL, "imgsz": FINAL_IMGSZ, **overall}
    save_metrics_csv(row, OUT_METRICS)
    save_metrics_csv(summarize_per_class(metrics), OUT_CLASS)

    cm = Path(metrics.save_dir) / "confusion_matrix.png"
    if cm.is_file():
        FIGURE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(cm, FIGURE_DIR / "final_test_confusion_matrix.png")

    print("\n[Frozen Test 결과]")
    for k, v in overall.items():
        print(f"  {k:<10} {v}")
    print(f"\n저장: {OUT_METRICS.relative_to(PROJECT_ROOT)}, {OUT_CLASS.relative_to(PROJECT_ROOT)}, "
          f"reports/figures/final_test_confusion_matrix.png")


if __name__ == "__main__":
    main()
