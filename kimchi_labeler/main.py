"""라벨링 프로그램 실행.

    python main.py
    python main.py --raw D:/data/kimchi_raw --worker 홍길동
"""
import argparse

from src.ui.app import run

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="조각김치 이물검출 라벨링")
    ap.add_argument("--raw", help="RAW 데이터 폴더 (기본: settings.json 의 raw_root)")
    ap.add_argument("--work", help="WORK 폴더 (기본: settings.json 의 work_root)")
    ap.add_argument("--worker", help="작업자 이름")
    a = ap.parse_args()
    run(a.raw, a.work, a.worker)
