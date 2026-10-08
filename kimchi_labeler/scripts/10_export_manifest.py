"""Dataset Manifest 제출용 내보내기 (산출물 7번).

    python scripts/10_export_manifest.py      -> manifests/dataset_manifest.csv

작업용 manifest.csv(WORK 폴더)는 그대로 두고, 제출 형식의 열 이름으로 새로 만든다.

  status     DONE    기존 라벨이 맞아서 수정 없이 검수 완료
             EDITED  라벨을 수정·추가·삭제한 뒤 저장
             REVIEW  판단이 어려워 추가 확인 필요
             PENDING 아직 검수 전
  qa_status  PASS    최종 검수 완료 (PASS · REVIEWED · FINAL)
             WAIT    교차검수 또는 QA 가 끝나지 않음
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import MANIFESTS_DIR, Paths  # noqa: E402
from src.yolo.dataset import scan_images  # noqa: E402
from src.manifest import Manifest  # noqa: E402
from src.bbox.session import canonical  # noqa: E402
from src.validation.validator import image_size  # noqa: E402
from src.yolo.yolo_io import read_label_file  # noqa: E402

COLUMNS = [
    "file_name", "relative_path",
    "source_dataset", "original_split",
    "scene_type", "worker", "reviewer",
    "status", "qa_status", "review_reason",
    "original_bbox_count", "final_bbox_count", "bbox_diff",
    "original_class_count", "final_class_count", "class_diff",
    "note", "updated_at"
    ]

QA_DONE = {"PASS", "REVIEWED", "FINAL"}


def label_changed(rec, paths) -> bool:
    w, h, _ = image_size(rec.raw_image(paths))
    raw = read_label_file(rec.raw_label(paths), w, h).boxes
    final = read_label_file(rec.effective_label(paths), w, h).boxes
    return canonical(raw, w, h) != canonical(final, w, h)


def submit_status(work_status: str, changed: bool) -> str:
    if work_status in ("", "PENDING", "WORKING"):
        return "PENDING"
    if work_status in ("REVIEW", "EDITED"):
        return work_status
    return "EDITED" if changed else "DONE"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw"); ap.add_argument("--work")
    ap.add_argument("--out", help="저장 위치 (기본: manifests/dataset_manifest.csv)")
    a = ap.parse_args()
    paths = Paths(a.raw, a.work)
    m = Manifest(paths.manifest)

    rows = []
    for rec in scan_images(paths.raw):
        r = m.rows.get(rec.rel_image)
        if r is None:
            continue
        status = submit_status(r["status"], label_changed(rec, paths))
        rows.append({
            "file_name": rec.image_name,
            "relative_path": rec.rel_image,
            "source_dataset": r["source_dataset"],
            "original_split": r["original_split"],
            "scene_type": r["scene_type"],
            "worker": r["assignee"] or r["updated_by"],
            "reviewer": r["reviewer"],
            "status": status,
            "qa_status": "PASS" if r["status"] in QA_DONE else "WAIT",
            "review_reason": r["issue"] if status == "REVIEW" or r["issue"] else "",
            "original_bbox_count": r["original_bbox_count"],
            "final_bbox_count": r["final_bbox_count"],
            "bbox_diff": r["bbox_diff"],
            "original_class_count": r["original_class_count"],
            "final_class_count": r["final_class_count"],
            "class_diff": r["class_diff"],
            "note": r["note"],
            "updated_at": r["updated_at"],
        })

    out = Path(a.out) if a.out else MANIFESTS_DIR / "dataset_manifest.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:      # 엑셀에서 한글이 깨지지 않게
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    count = {}
    for row in rows:
        key = (row["status"], row["qa_status"])
        count[key] = count.get(key, 0) + 1
    print(f"저장: {out}  ({len(rows)}행)")
    for (st, qa), n in sorted(count.items()):
        print(f"  {st:8} / {qa:4} : {n}")


if __name__ == "__main__":
    main()
