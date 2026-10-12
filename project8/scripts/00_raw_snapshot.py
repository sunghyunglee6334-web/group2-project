"""RAW 원본 보호 확인: 모든 RAW 파일의 SHA-256 을 기록/비교한다.

    python scripts/00_raw_snapshot.py            # 처음 1번: 기준 해시 생성
    python scripts/00_raw_snapshot.py --verify   # 이후: RAW 가 바뀌지 않았는지 확인
"""
import argparse
import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import Paths  # noqa: E402


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--raw")
    ap.add_argument("--work")
    a = ap.parse_args()
    paths = Paths(a.raw, a.work)
    raw = paths.raw
    SNAP = paths.work / "raw_checksums.csv"   # WORK 폴더에 보관 (병합 시 함께 이동)
    files = sorted(p for p in raw.rglob("*") if p.is_file())
    current = {p.relative_to(raw).as_posix(): sha256(p) for p in files}
    if not a.verify:
        SNAP.parent.mkdir(parents=True, exist_ok=True)
        with open(SNAP, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["relative_path", "sha256"])
            w.writerows(sorted(current.items()))
        print(f"RAW 기준 해시 저장: {len(current)}개 파일 -> {SNAP}")
        return 0
    if not SNAP.exists():
        print("기준 해시가 없습니다. 먼저 --verify 없이 실행하세요.")
        return 2
    with open(SNAP, encoding="utf-8") as f:
        base = {r["relative_path"]: r["sha256"] for r in csv.DictReader(f)}
    changed = [k for k in base if k in current and base[k] != current[k]]
    missing = [k for k in base if k not in current]
    added = [k for k in current if k not in base]
    for title, items in (("변경됨", changed), ("사라짐", missing), ("새로 생김", added)):
        for k in items:
            print(f"[{title}] {k}")
    if changed or missing or added:
        print(f"[FAIL] RAW 가 바뀌었습니다! 변경 {len(changed)} / 사라짐 {len(missing)} / 추가 {len(added)}")
        return 1
    print(f"[OK] RAW {len(base)}개 파일이 처음과 동일합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
