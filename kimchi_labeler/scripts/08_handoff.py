"""교과 8 Handoff 문서 자동 생성 (FINAL 생성 후 실행).

    python scripts/08_handoff.py   -> docs/subject08_handoff.md  (산출물 11번)
"""
import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import CLASS_NAMES, DOCS_DIR, Paths  # noqa: E402

spec = importlib.util.spec_from_file_location("qa", ROOT / "scripts" / "05_qa_summary.py")
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw"); ap.add_argument("--work"); ap.add_argument("--final")
    ap.add_argument("--out", help="저장 위치 (기본: docs/subject08_handoff.md)")
    a = ap.parse_args()
    paths = Paths(a.raw, a.work, a.final)
    if not (paths.final / "manifest_final.csv").exists():
        raise SystemExit("FINAL 이 없습니다. 07_build_final.py 를 먼저 실행하세요.")
    body = qa.build(paths, label_root=paths.final, title="교과 8 Handoff - 조각김치 이물검출 FINAL 데이터")
    extra = [
        "## 위치", "",
        f"- FINAL 이미지: `{paths.final}/images/`, 라벨: `{paths.final}/labels/` (같은 파일명 Pair)",
        "- 원래 Dataset / split: `final_file_map.csv`, `manifest_final.csv` 의 source_dataset · original_split",
        "- Dataset Manifest: `manifests/dataset_manifest.csv` (10_export_manifest.py)",
        "- Class 설정: `configs/classes.yaml`, 판단 기준: `docs/class_guide.md`, BBox 기준: `docs/bbox_guide.md`",
        "- QA 결과: `reports/qa_summary.md`, 프로그램 테스트: `reports/test_report.md`",
        "- 라벨링 프로그램: `bash run.sh` (README 참고)", "",
        "## Class ID (변경 없음)", "", "| ID | 이름 |", "|---:|---|",
        *[f"| {k} | {v} |" for k, v in CLASS_NAMES.items()], "",
        "## 교과 8 주의사항", "",
        "- 기존 train / validation 구분을 교과 7 에서 섞지 않았습니다. 최종 split 은 교과 8 에서 결정합니다.",
        "- Class 4(고무장갑)는 사용하지 않는 Class 입니다. 처리 근거는 Manifest note 를 확인하세요.",
        "- 빈 TXT 는 사람이 확인한 정상(Negative) 이미지입니다.",
        "- object_only 이미지 성능이 김치 배경 성능을 보장하지 않습니다. scene_type 별로 따로 평가하세요.",
        "- 비슷한 장면/중복 이미지가 train 과 validation 에 나뉘어 있으면 Data Leakage 를 점검하세요.",
        "- 본 데이터는 100% 가상 생성 교육용 데이터이며 NDA 대상입니다.", ""]
    out = Path(a.out) if a.out else DOCS_DIR / "subject08_handoff.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body + "\n" + "\n".join(extra), encoding="utf-8")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
