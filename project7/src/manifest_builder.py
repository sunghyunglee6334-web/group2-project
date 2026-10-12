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

def count_raw_classes(rec: ImageRecord, paths: Paths) -> str:
    p = rec.raw_label(paths)
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    classes = {line.split()[0] for line in text.splitlines() if line.strip()}
    return str(len(classes))

def count_work_stats(rec: ImageRecord, paths: Paths) -> tuple[str, str]:
    p = rec.work_label(paths)
    if not p.exists():
        return "", ""
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    classes = {line.split()[0] for line in lines}
    return str(len(lines)), str(len(classes))

def normalize_manifest_paths(manifest: Manifest, paths: Paths) -> None:
    dataset = paths.raw.name
    if not dataset.startswith("이물검출_학습데이터"):
        return

    prefix = f"{dataset}/"
    migrated = {}

    for key, row in list(manifest.rows.items()):
        if not key.startswith("images/"):
            continue

        new_key = prefix + key
        if new_key in manifest.rows:
            continue

        new_row = row.copy()
        new_row["relative_path"] = new_key
        new_row["source_dataset"] = dataset

        label = new_row["label_relative_path"]
        if label and not label.startswith(prefix):
            new_row["label_relative_path"] = prefix + label

        migrated[new_key] = new_row
        del manifest.rows[key]

    for key, row in migrated.items():
        manifest.rows[key] = row

def add_records(manifest: Manifest, records: list[ImageRecord], paths: Paths) -> int:
    """Manifest 에 없는 이미지만 PENDING 으로 추가하고, 기존 행의 누락된 원본 통계를 보완한다."""
    normalize_manifest_paths(manifest, paths)
    added = 0
    for rec in records:
        if rec.rel_image in manifest.rows:
            row = manifest.rows[rec.rel_image]

            if not row["original_class_count"]:
                row["original_class_count"] = count_raw_classes(rec, paths)

            final_bbox_count, final_class_count = count_work_stats(rec, paths)

            if final_bbox_count:
                if not row["final_bbox_count"]:
                    row["final_bbox_count"] = final_bbox_count
                if not row["bbox_diff"] and row["original_bbox_count"]:
                    row["bbox_diff"] = str(
                        int(row["final_bbox_count"]) - int(row["original_bbox_count"])
                    )

            if final_class_count:
                if not row["final_class_count"]:
                    row["final_class_count"] = final_class_count
                if not row["class_diff"] and row["original_class_count"]:
                    row["class_diff"] = str(
                        int(row["final_class_count"]) - int(row["original_class_count"])
                    )

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
            original_class_count=count_raw_classes(rec, paths),
            updated_at=now_str(),
            updated_by="builder",
        )
        manifest.rows[rec.rel_image] = row
        added += 1
    return added
