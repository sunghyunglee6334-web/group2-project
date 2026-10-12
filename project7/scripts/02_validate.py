"""자동 Validation. 자동으로 고치지 않고 보고서만 만든다.

    python scripts/02_validate.py --target raw    # RAW 원본 사전검사 (위험 이미지 찾기)
    python scripts/02_validate.py                 # WORK 저장본 기준 (없으면 RAW)
종료코드: CRITICAL 이 있으면 1
"""
import argparse
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import REPORT_DIR, Paths  # noqa: E402
from src.validation.validator import critical_count, summarize, validate, write_report  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["raw", "work"], default="work")
    ap.add_argument("--raw")
    ap.add_argument("--work")
    a = ap.parse_args()
    paths = Paths(a.raw, a.work)
    issues = validate(paths, use_work=(a.target == "work"))
    out = REPORT_DIR / f"validation_{a.target}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    write_report(issues, out)
    for sev, codes in summarize(issues).items():
        for code, n in codes.items():
            print(f"[{sev}] {code}: {n}")
    n = critical_count(issues)
    print(f"\nCRITICAL {n}건  ->  보고서 {out}")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
