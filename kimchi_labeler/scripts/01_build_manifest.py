"""RAW 를 조사해 Manifest(data/work/manifest.csv)를 만들고 Data Inventory 를 출력한다.
이미 있는 행(작업 기록)은 건드리지 않고 새 이미지만 추가한다.

    python scripts/01_build_manifest.py
"""
import argparse
from collections import Counter
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import Paths  # noqa: E402
from src.yolo.dataset import scan_images, scan_orphan_labels  # noqa: E402
from src.manifest import Manifest  # noqa: E402
from src.manifest_builder import add_records  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw")
    ap.add_argument("--work")
    a = ap.parse_args()
    paths = Paths(a.raw, a.work)
    paths.check_not_same()
    recs = scan_images(paths.raw)
    m = Manifest(paths.manifest)
    added = add_records(m, recs, paths)
    m.save()
    print(f"Manifest: {paths.manifest}  (전체 {len(m.rows)}행, 이번에 추가 {added}행)")
    print("\n[Data Inventory]")
    print(f"이미지 수: {len(recs)}")
    for k, v in sorted(Counter(f'{r.source_dataset}/{r.original_split}' for r in recs).items()):
        print(f"  {k}: {v}")
    no_txt = [r for r in recs if not r.raw_label(paths).exists()]
    empty = [r for r in recs if r.raw_label(paths).exists()
             and not r.raw_label(paths).read_text(encoding='utf-8-sig').strip()]
    orphans = scan_orphan_labels(paths.raw, recs)
    print(f"TXT 없음: {len(no_txt)}   빈 TXT: {len(empty)}   짝 없는 TXT: {len(orphans)}")
    names = Counter(r.image_name for r in recs)
    dup = [n for n, c in names.items() if c > 1]
    if dup:
        print(f"[주의] Dataset 간 같은 파일명 {len(dup)}개 -> 파일명이 아닌 relative_path 로 구분합니다.")


if __name__ == "__main__":
    main()
