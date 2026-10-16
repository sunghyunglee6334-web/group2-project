"""5~6일차: Val 전체에서 실패 후보를 모아 비교 그림과 failure_analysis 초안을 만든다.
실행 (project8 폴더에서, compare_gt_pred.py 다음에):
    python scripts/09_collect_failures.py"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluate_detector import save_metrics_csv        # noqa: E402
from src.failure_analyzer import analyze_image, count_types  # noqa: E402
from src.label_visualizer import visualize                # noqa: E402
from src.split_builder import CLASS_NAMES                 # noqa: E402

IMAGE_DIR = PROJECT_ROOT / "data" / "yolo" / "images" / "val"
LABEL_DIR = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"
PRED_DIR = PROJECT_ROOT / "runs" / "pred_val" / "labels"      # compare_gt_pred.py 결과
VAL_CSV = PROJECT_ROOT / "manifests" / "val.csv"
OUT_IMG = PROJECT_ROOT / "runs" / "failure_candidates"
SUMMARY_CSV = PROJECT_ROOT / "reports" / "failure_summary.csv"
DRAFT_CSV = PROJECT_ROOT / "reports" / "failure_analysis_draft.csv"
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
FAIL_TYPES = ("FN", "FP", "CLASS", "BBOX")                    # TP 는 실패가 아님


def load_val_info(val_csv):
    """val.csv 를 읽어 {이미지 이름(확장자 제외): {"source_dataset", "scene_type"}} 로 돌려준다."""
    # TODO A
    pass


def collect(images, info):
    """이미지마다 판정해서 (요약 줄 목록, 실패 박스 줄 목록) 을 돌려준다.
    요약은 실패 개수가 많은 이미지부터 정렬한다."""
    # TODO B
    pass


def save_failure_images(summary_rows):
    """실패가 있는 이미지만 비교 그림을 그려 유형별 폴더에 저장하고, 저장한 장수를 돌려준다."""
    # TODO C
    pass


def main():
    """준비물 확인 → 정보 읽기 → 판정 → CSV 2개 저장 → 그림 저장 → 요약 출력"""
    # TODO D
    pass


if __name__ == "__main__":
    main()