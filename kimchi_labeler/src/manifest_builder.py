"""RAW 를 조사해 Manifest 행을 만든다."""
from __future__ import annotations

from .config import Paths
from .manifest import COLUMNS, Manifest, now_str
from .yolo.dataset import ImageRecord


def count_raw_boxes(rec: ImageRecord, paths: Paths) -> str:
    p = rec.raw_label(paths)
    if not p.exists():
        return ""          # TXT 없음 -> 빈칸 (Validation 에서 CRITICAL)
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    return str(sum(1 for line in text.splitlines() if line.strip()))


def add_records(manifest: Manifest, records: list[ImageRecord], paths: Paths) -> int:
    """Manifest 에 없는 이미지만 PENDING 으로 추가한다. 기존 행은 건드리지 않는다."""
    added = 0
    for rec in records:
        if rec.rel_image in manifest.rows:
            continue
        row = {c: "" for c in COLUMNS}
        row.update(
            relative_path=rec.rel_image,
            image_name=rec.image_name,
            label_name=rec.label_name,
            label_relative_path=rec.rel_label,
            source_dataset=rec.source_dataset,
            original_split=rec.original_split,
            status="PENDING",
            original_bbox_count=count_raw_boxes(rec, paths),
            updated_at=now_str(),
            updated_by="builder",
        )
        manifest.rows[rec.rel_image] = row
        added += 1
    return added
