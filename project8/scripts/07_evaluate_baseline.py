"""5일차: Baseline 모델을 Validation 에서 평가하고 산출물 2·5 파일을 만든다.
실행: 프로젝트 루트에서  python scripts/07_evaluate_baseline.py"""

import shutil
import sys
from pathlib import Path

# 프로젝트 루트 잡기
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 부품 가져오기
from src.evaluate_detector import (
    evaluate_detector, summarize_overall, summarize_per_class, save_metrics_csv,
)

# 학습조건 + 숫자 4개 
# TODO: baseline_training_condition.md와 똑같이 맞추기!!!
CONFIG = {
    "model_version": "baseline_v1",
    "dataset_version": "kimchi_v1",
    "split": "val",
    "imgsz": 640,
    "batch": 8,
    "epochs": 70,
    "patience": 30,
    "seed": 42,
}

# 파일위치
WEIGHT = PROJECT_ROOT / "models" / "baseline" / "baseline_best.pt"
DATA_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
TRAIN_RUN = PROJECT_ROOT / "runs" / "baseline_v1"
REPORTS = PROJECT_ROOT / "reports"
FIGURES = REPORTS / "figures"

# YOLO 가 만든 그림을 reports/figures 로 복사 (없으면 건너뜀
def copy_figure(src, dst):
    if Path(src).is_file():
        FIGURES.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        print("그림 저장:", dst)
    else:
        print("그림 없음(건너뜀):", src)


def main():
    # 1단계: 평가
    metrics = evaluate_detector(str(WEIGHT), str(DATA_YAML),
                                split=CONFIG["split"], imgsz=CONFIG["imgsz"],
                                project=PROJECT_ROOT / "runs" / "val", name=CONFIG["model_version"])

    # 2단계: CSV 저장
    row = {**CONFIG, **summarize_overall(metrics)}
    print("저장:", save_metrics_csv(row, REPORTS / "baseline_metrics.csv"))
    print(row)

    # 3단계: Class별 성능 화면 출력
    print("\n[Class별 성능]")
    per_class = summarize_per_class(metrics)
    print("저장:", save_metrics_csv(per_class, REPORTS / "baseline_class_metrics.csv"))
    for r in per_class:
        print(f"{r['class_id']} {r['class_name']:<22} "
              f"P={r['precision']}  R={r['recall']}  mAP50={r['map50']}")

    # 4단계: 그림 복사
    copy_figure(Path(metrics.save_dir) / "confusion_matrix.png",
                FIGURES / "baseline_confusion_matrix.png")
    copy_figure(TRAIN_RUN / "results.png", FIGURES / "baseline_results.png")


if __name__ == "__main__":
    main()