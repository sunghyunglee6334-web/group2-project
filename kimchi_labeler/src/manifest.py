"""Dataset Manifest.

900장의 출처·split·장면유형·작업자·상태·검수이력을 한 CSV 로 관리한다.
엑셀에서 한글이 깨지지 않도록 utf-8-sig 로 저장한다.
키 = relative_path (RAW 기준 이미지 상대경로)
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from .yolo.yolo_io import atomic_write_text

COLUMNS = [
    "relative_path", "image_name", "label_name", "label_relative_path",
    "source_dataset", "original_split", "scene_type",
    "assignee", "reviewer", "status",
    "original_bbox_count", "final_bbox_count",
    "issue", "note", "pilot", "pass_sample", "updated_at", "updated_by",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Manifest:
    def __init__(self, path: Path):
        self.path = path
        self.rows: dict[str, dict] = {}     # relative_path -> row
        if path.exists():
            self.load()

    # ------------------------------------------------ IO
    def load(self) -> None:
        with open(self.path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                full = {c: row.get(c, "") or "" for c in COLUMNS}
                self.rows[full["relative_path"]] = full

    def save(self) -> None:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for key in sorted(self.rows):
            w.writerow(self.rows[key])
        # utf-8-sig BOM 을 붙여 엑셀 호환
        atomic_write_text(self.path, "﻿" + buf.getvalue())

    # ------------------------------------------------ 조회/수정
    def get(self, rel: str) -> dict:
        return self.rows[rel]

    def update(self, rel: str, by: str = "", **fields) -> None:
        row = self.rows[rel]
        for k, v in fields.items():
            if k not in COLUMNS:
                raise KeyError(f"Manifest 에 없는 컬럼: {k}")
            row[k] = "" if v is None else str(v)
        row["updated_at"] = now_str()
        if by:
            row["updated_by"] = by

    def keys(self) -> list[str]:
        return sorted(self.rows)

    def count_by(self, col: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.rows.values():
            out[r[col]] = out.get(r[col], 0) + 1
        return dict(sorted(out.items()))


def _rank(row: dict) -> tuple:
    """최신 기록 우선. 같은 시각이면 사람이 작업한 기록이 배분/생성 기록보다 우선."""
    return row["updated_at"], row["updated_by"] not in ("", "builder", "assign")


def merge_manifests(paths: list[Path]) -> tuple[dict[str, dict], dict[str, Path]]:
    """여러 팀원의 manifest 를 합친다. 같은 이미지는 updated_at 이 가장 최신인 행이 이긴다.
    반환: (rows, 각 행을 가져온 manifest 경로)"""
    merged: dict[str, dict] = {}
    origin: dict[str, Path] = {}
    for p in paths:
        m = Manifest(p)
        for key, row in m.rows.items():
            cur = merged.get(key)
            if cur is None or _rank(row) > _rank(cur):
                merged[key] = row
                origin[key] = p
    return merged, origin
