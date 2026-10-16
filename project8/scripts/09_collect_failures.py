"""Val 전체에서 실패 후보를 모아 비교 그림과 failure_analysis 초안을 만든다.
실행 (project8 폴더에서, compare_gt_pred.py 다음에): python scripts/09_collect_failures.py"""

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

def class_name(class_id):
    """Class 번호 → 이름. 짝이 없으면(None) "none"."""
    if class_id is None:
        return "none"
    return CLASS_NAMES.get(class_id, str(class_id))


def load_val_info(val_csv):
    """val.csv 를 읽어 {이미지 이름(확장자 제외): {"source_dataset", "scene_type"}} 로 돌려준다."""
    df = pd.read_csv(val_csv, encoding="utf-8-sig")

    # 1 필요한 컬럼이 있는지 먼저 확인
    need = ["image_name", "source_dataset", "scene_type"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"val.csv 에 필요한 컬럼이 없습니다: {missing}")

    # 2 빈칸(NaN)은 빈 글자로
    df = df[need].fillna("")

    # 3 이름 → 정보 사전
    info = {}
    for name, source, scene in zip(df["image_name"], df["source_dataset"], df["scene_type"]):
        info[Path(name).stem] = {"source_dataset": source, "scene_type": scene}
    return info


def collect(images, info, label_dir=LABEL_DIR, pred_dir=PRED_DIR):
    """이미지마다 판정해서 (요약 줄 목록, 실패 박스 줄 목록) 을 돌려준다.
    요약은 실패 개수가 많은 이미지부터 정렬한다."""
    summary, fails = [], []
    for img in images:
        # 1 val.csv 정보 (없으면 빈칸)
        meta = info.get(img.stem, {"source_dataset": "", "scene_type": ""})

        # 2 판정과 개수
        results = analyze_image(label_dir / f"{img.stem}.txt", pred_dir / f"{img.stem}.txt")
        counts = count_types(results)
        n_fail = sum(counts[t] for t in FAIL_TYPES)

        # 3 요약표: 이미지 한 장 = 한 줄
        summary.append({"image": img.name, **meta, **counts, "n_fail": n_fail})

        # 4 초안표: 실패 박스 한 개 = 한 줄 (가이드 failure_analysis.csv 컬럼)
        for r in results:
            if r["failure_type"] == "TP":
                continue
            fails.append({
                "image": img.name, **meta,
                "failure_type": r["failure_type"],
                "ground_truth": class_name(r["gt_class"]),
                "prediction": class_name(r["pred_class"]),
                "confidence": "" if r["confidence"] is None else round(r["confidence"], 3),
                "iou": r["iou"],
                "suspected_cause": "", "evidence": "", "next_action": "",   # 사람이 채움
            })

    # 5 실패 많은 이미지부터
    summary.sort(key=lambda row: row["n_fail"], reverse=True)
    order = {row["image"]: i for i, row in enumerate(summary)}
    fails.sort(key=lambda row: order[row["image"]])
    return summary, fails


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