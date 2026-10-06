"""QA Summary(Markdown) 자동 생성. 매일 마감 때 실행해서 진행 상황 확인에도 사용.

    python scripts/05_qa_summary.py            -> reports/qa_summary.md  (산출물 8번)
"""
import argparse
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import REPORT_DIR, Paths  # noqa: E402
from src.yolo.dataset import scan_images  # noqa: E402
from src.manifest import Manifest  # noqa: E402
from src.validation.stats import class_table, collect, counter_table  # noqa: E402
from src.validation.validator import critical_count, summarize, validate  # noqa: E402


def build(paths: Paths, label_root=None, title="QA Summary") -> str:
    recs = scan_images(paths.raw)
    m = Manifest(paths.manifest)
    st = collect(paths, recs, m, label_root)
    issues = validate(paths, use_work=True, records=recs) if label_root is None else []
    d = st["diff"]
    L = [f"# {title}", "", f"- 생성: {datetime.now():%Y-%m-%d %H:%M}",
         "- 데이터: AI캠퍼스 교육용 **100% 가상 생성** 조각김치 이물검출 데이터 (NDA, 외부 유출 금지)", "",
         "## 1. 수량", "",
         f"| 항목 | 값 |", "|---|---:|",
         f"| 이미지 | {st['images']} |", f"| 최종 TXT | {st['txt_final']} |",
         f"| 빈 TXT(BBox 0개) | {st['empty_final']} |",
         f"| 전체 BBox (RAW → 최종) | {sum(st['class_raw'].values())} → {sum(st['class_final'].values())} |", "",
         *counter_table("Dataset/split", st["by_source_split"]), "",
         *counter_table("scene_type", st["by_scene"]), "",
         "## 2. Class 별 BBox", "", *class_table(st), "",
         "## 3. 라벨 보정 내역 (RAW 대비)", "",
         "| 항목 | 수 |", "|---|---:|",
         f"| 그대로 유지 | {d['same']} |", f"| 위치·크기 수정 | {d['moved']} |",
         f"| Class 변경 | {d['class_changed']} |", f"| 추가 | {d['added']} |", f"| 삭제 | {d['deleted']} |", "",
         "## 4. 작업 상태", "", *counter_table("status", st["by_status"]), "",
         *counter_table("담당자", st["by_assignee"]), "",
         f"- Pilot 이미지: {st['pilot']}장",
         f"- 교차검수 완료(REVIEWED/FINAL + reviewer 기록): {st['reviewed']}장",
         f"- PASS 표본검수: 선정 {st['pass_sample']}장 / 완료 {st['pass_sample_done']}장", ""]
    if label_root is None:
        L += ["## 5. 자동 Validation (WORK 기준)", "", f"- CRITICAL: **{critical_count(issues)}건**"]
        for sev, codes in summarize(issues).items():
            for code, n in codes.items():
                L.append(f"- [{sev}] {code}: {n}")
        rem = st["by_status"].get("REVIEW", 0) + st["by_status"].get("PENDING", 0) + st["by_status"].get("WORKING", 0)
        L += ["", "## 6. 최종 목표 체크", "",
              f"- [{'x' if critical_count(issues) == 0 else ' '}] Critical Validation Error = 0",
              f"- [{'x' if st['by_status'].get('REVIEW', 0) == 0 else ' '}] 미처리 REVIEW = 0",
              f"- [{'x' if rem == 0 else ' '}] PENDING/WORKING/REVIEW 잔여 = 0 (현재 {rem})",
              f"- [{'x' if st['by_status'].get('EDITED', 0) == 0 else ' '}] EDITED 전부 교차검수 완료 (남은 EDITED {st['by_status'].get('EDITED', 0)})"]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw"); ap.add_argument("--work")
    ap.add_argument("--out", help="저장 위치 (기본: reports/qa_summary.md)")
    a = ap.parse_args()
    out = Path(a.out) if a.out else REPORT_DIR / "qa_summary.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(Paths(a.raw, a.work)), encoding="utf-8")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
