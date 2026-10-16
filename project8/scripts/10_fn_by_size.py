"""Val 놓친 박스(FN)를 Class × 크기(small/medium/large)로 세는 표

실행 : python scripts/10_fn_by_size.py
입력 : data/yolo/images/val, data/yolo/labels/val, runs/pred_val/labels, reports/split_report.md
출력 : reports/fn_by_size.csv
"""
import ast
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.failure_analyzer import analyze_image
from src.label_visualizer import read_yolo_labels
from src.split_builder import CLASS_NAMES

IMAGE_DIR = PROJECT_ROOT / "data" / "yolo" / "images" / "val"
LABEL_DIR = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"
PRED_DIR = PROJECT_ROOT / "runs" / "pred_val" / "labels"
REPORT_MD = PROJECT_ROOT / "reports" / "split_report.md"
OUT_CSV = PROJECT_ROOT / "reports" / "fn_by_size.csv"
TRAIN_PX = 640
SIZES = ["small", "medium", "large"]


def load_bins(md_path):
    """split_report.md 의 크기 경계 줄에서 Class별 (small 경계, large 경계) px 를 읽는다."""
    text = Path(md_path).read_text(encoding="utf-8")
    m = re.search(r"small < (\{.*?\})px ≤ medium < (\{.*?\})px", text)
    if m is None:
        raise ValueError(f"크기 경계 줄을 찾지 못했습니다: {md_path}")
    small, large = ast.literal_eval(m.group(1)), ast.literal_eval(m.group(2))
    return {int(c): (small[c], large[c]) for c in small}


def size_bin(w, h, img_wh, cut):
    """YOLO 비율 w·h → 긴 변 640 기준 √넓이(px) → small/medium/large (Split 과 같은 방식)"""
    W, H = img_wh
    scale = TRAIN_PX / max(W, H)
    side = ((w * W * scale) * (h * H * scale)) ** 0.5
    lo, hi = cut
    return "small" if side < lo else "large" if side >= hi else "medium"


def count_by_size(images, label_dir, pred_dir, bins):
    """Class × 크기별 정답 수, 놓친 수, 놓친 비율 표를 만든다."""
    gt_n, fn_n = Counter(), Counter()
    for img in images:
        wh = Image.open(img).size
        gt_txt, pred_txt = label_dir / f"{img.stem}.txt", pred_dir / f"{img.stem}.txt"
        for g in read_yolo_labels(gt_txt):
            gt_n[(g[0], size_bin(g[3], g[4], wh, bins[g[0]]))] += 1
        for r in analyze_image(gt_txt, pred_txt):
            if r["failure_type"] == "FN":
                c = r["gt_class"]
                fn_n[(c, size_bin(r["gt_w"], r["gt_h"], wh, bins[c]))] += 1

    rows = []
    for c in sorted({c for c, _ in gt_n}) + ["all"]:
        for z in SIZES:
            if c == "all":
                n = sum(v for (_, s), v in gt_n.items() if s == z)
                miss = sum(v for (_, s), v in fn_n.items() if s == z)
            else:
                n, miss = gt_n[(c, z)], fn_n[(c, z)]
            rows.append({"class": c, "class_name": CLASS_NAMES.get(c, "all"), "size": z,
                         "gt": n, "fn": miss, "miss_rate": round(miss / n, 3) if n else None})
    return pd.DataFrame(rows)


def main():
    bins = load_bins(REPORT_MD)
    images = sorted(p for p in IMAGE_DIR.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    df = count_by_size(images, LABEL_DIR, PRED_DIR, bins)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(df.to_string(index=False))
    print(f"저장: {OUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()