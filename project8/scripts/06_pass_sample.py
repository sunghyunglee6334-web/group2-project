"""PASS 표본검수 대상 선정 (권장 20~30%).

작은 BBox / BBox 많은 이미지 / 희소 Class 를 우선 뽑고, 나머지는 무작위.
선정된 이미지는 GUI 의 '내 검수 대상' / 'PASS 표본검수' 보기에 나타난다.
검수자는 이상 없으면 REVIEWED, 문제 있으면 수정 후 EDITED + Note.

    python scripts/06_pass_sample.py --ratio 0.25
"""
import argparse
import random
from collections import Counter
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import Paths  # noqa: E402
from src.manifest import Manifest  # noqa: E402
from src.validation.validator import image_size  # noqa: E402
from src.yolo.dataset import scan_images  # noqa: E402
from src.yolo.yolo_io import read_label_file  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--raw"); ap.add_argument("--work")
    a = ap.parse_args()
    paths = Paths(a.raw, a.work)
    m = Manifest(paths.manifest)
    recs = {r.rel_image: r for r in scan_images(paths.raw)}
    pass_rows = [r for r in m.rows.values() if r["status"] == "PASS" and r["relative_path"] in recs]
    class_freq = Counter()
    info = {}
    for r in pass_rows:
        rec = recs[r["relative_path"]]
        w, h, _ = image_size(rec.raw_image(paths))
        boxes = read_label_file(rec.effective_label(paths), w, h).boxes
        info[r["relative_path"]] = (w, h, boxes)
        class_freq.update(b.cls for b in boxes)
    rare = {c for c, _ in class_freq.most_common()[-2:]} if class_freq else set()

    def risk(key: str) -> float:
        w, h, boxes = info[key]
        small = sum(1 for b in boxes if b.w * b.h < 0.001 * w * h)
        return small * 2 + len(boxes) + 3 * sum(1 for b in boxes if b.cls in rare) + random.random()

    random.seed(a.seed)
    already = sum(1 for r in pass_rows if r["pass_sample"] == "1")
    need = max(0, round(len(pass_rows) * a.ratio) - already)
    cands = sorted((r for r in pass_rows if r["pass_sample"] != "1"),
                   key=lambda r: risk(r["relative_path"]), reverse=True)
    half = need // 2   # 절반은 위험도 순, 절반은 무작위
    chosen = cands[:half]
    rest = cands[half:]
    chosen += random.sample(rest, min(len(rest), need - half))
    for r in chosen:
        r["pass_sample"] = "1"
    m.save()
    print(f"PASS {len(pass_rows)}장 중 표본 {already + len(chosen)}장 선정 (이번 추가 {len(chosen)})")


if __name__ == "__main__":
    main()
