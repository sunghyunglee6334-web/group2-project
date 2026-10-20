"""Auto Label 후보와 Human Review 결과를 이미지별 CSV 한 행으로 관리한다."""
from __future__ import annotations

import csv
from pathlib import Path


REVIEW_COLUMNS = [
    "input_image", "candidate_label", "reviewed_label", "auto_label_status",
    "candidate_bbox_count", "final_bbox_count", "review_status", "accepted_unchanged",
    "class_edits", "bbox_edits", "deleted", "added", "review_count", "reviewed_by",
    "reviewed_at",
]
REVIEW_FIELDS = (
    "reviewed_label", "final_bbox_count", "review_status", "accepted_unchanged",
    "class_edits", "bbox_edits", "deleted", "added", "review_count", "reviewed_by",
    "reviewed_at",
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def register_candidates(
    report_path: str | Path,
    run_rows: list[dict[str, object]],
) -> None:
    """Auto Label 실행 행을 upsert한다. 새 후보 생성 시 이전 검수결과는 초기화한다."""
    path = Path(report_path)
    rows = _read_rows(path)
    by_candidate = {row.get("candidate_label", ""): row for row in rows}

    for result in run_rows:
        candidate = str(result.get("candidate_label", ""))
        if not candidate:
            continue
        row = by_candidate.get(candidate)
        if row is None:
            row = {column: "" for column in REVIEW_COLUMNS}
            row["candidate_label"] = candidate
            rows.append(row)
            by_candidate[candidate] = row

        row.update({
            "input_image": result.get("input_image", ""),
            "candidate_label": candidate,
            "auto_label_status": result.get("status", ""),
        })
        if result.get("status") == "OK":
            row["candidate_bbox_count"] = result.get("detection_count", "")
            for field in REVIEW_FIELDS:
                row[field] = ""

    _write_rows(path, rows)


def update_review_result(
    report_path: str | Path,
    *,
    input_image: str,
    candidate_label: str,
    reviewed_label: str,
    candidate_bbox_count: int,
    final_bbox_count: int,
    review_status: str,
    accepted_unchanged: int,
    actions: dict[str, int],
    reviewed_by: str,
    reviewed_at: str,
) -> None:
    """검수 완료 행을 후보 실행 때 만든 같은 행에 기록한다."""
    path = Path(report_path)
    rows = _read_rows(path)
    row = next((item for item in rows if item.get("candidate_label") == candidate_label), None)
    if row is None:
        row = {column: "" for column in REVIEW_COLUMNS}
        row["candidate_label"] = candidate_label
        rows.append(row)

    row.update({
        "input_image": input_image,
        "candidate_label": candidate_label,
        "reviewed_label": reviewed_label,
        "auto_label_status": row.get("auto_label_status") or "OK",
        "candidate_bbox_count": row.get("candidate_bbox_count") or candidate_bbox_count,
        "final_bbox_count": final_bbox_count,
        "review_status": review_status,
        "accepted_unchanged": accepted_unchanged,
        "class_edits": actions.get("class_edits", 0),
        "bbox_edits": actions.get("bbox_edits", 0),
        "deleted": actions.get("deleted", 0),
        "added": actions.get("added", 0),
        "review_count": 1,
        "reviewed_by": reviewed_by,
        "reviewed_at": reviewed_at,
    })
    _write_rows(path, rows)
