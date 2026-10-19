"""
08_compare_gt_pred.py — 정답(GT)과 예측(Prediction)을 한 사진에 같이 그려 비교

실행 (project8 폴더에서, 07_evaluate_baseline.py 다음에):
    python scripts/08_compare_gt_pred.py              Val 전체
    python scripts/08_compare_gt_pred.py --n 20       Val 20장만

입력 : models/baseline/baseline_best.pt, data/yolo/images/val, data/yolo/labels/val
출력 : runs/pred_val/labels/*.txt      예측 TXT (YOLO 형식 + 확신도)
       runs/compare_val/*.jpg          GT = 실선, Pred = 점선 + 확신도
"""
from pathlib import Path
import argparse
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO  # noqa: E402

from src.split_builder import CLASS_NAMES  # noqa: E402
from src.label_visualizer import visualize  # noqa: E402

WEIGHT = PROJECT_ROOT / "models" / "baseline" / "baseline_best.pt"
IMAGE_DIR = PROJECT_ROOT / "data" / "yolo" / "images" / "val"
LABEL_DIR = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"
PRED_RUN = PROJECT_ROOT / "runs" / "pred_val"
OUT_DIR = PROJECT_ROOT / "runs" / "compare_val"
CONF = 0.25          # 이 확신도 이상인 예측만 그림
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def predict(images):
    """[1] 예측해서 TXT로 저장 (runs/pred_val/labels/이름.txt)"""
    model = YOLO(str(WEIGHT))
    for img in images:      # 한 장씩 → 메모리 절약
        model.predict(str(img), imgsz=640, conf=CONF, save_txt=True, save_conf=True,
                      project=str(PRED_RUN.parent), name=PRED_RUN.name, exist_ok=True, verbose=False)
    return PRED_RUN / "labels"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="앞에서 몇 장만 (0 = 전체)")
    a = ap.parse_args()

    for need in (WEIGHT, IMAGE_DIR, LABEL_DIR):
        if not need.exists():
            sys.exit(f"없습니다: {need.relative_to(PROJECT_ROOT)}")

    images = sorted(p for p in IMAGE_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if a.n:
        images = images[: a.n]

    pred_dir = predict(images)                                         # [1] 예측
    no_pred = 0
    for img in images:                                                 # [2] GT + Pred 그리기
        pred_txt = pred_dir / f"{img.stem}.txt"                        # 예측이 없으면 파일도 없음
        no_pred += not pred_txt.is_file()
        visualize(img, LABEL_DIR / f"{img.stem}.txt", OUT_DIR / f"{img.stem}.jpg",
                  CLASS_NAMES, pred_txt=pred_txt)
    print(f"비교 그림 {len(images)}장 → {OUT_DIR.relative_to(PROJECT_ROOT)} (예측 없음 {no_pred}장)")


if __name__ == "__main__":
    main()
