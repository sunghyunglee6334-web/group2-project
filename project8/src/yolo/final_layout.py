"""FINAL 데이터 폴더 규칙 (교과 7 산출물 3번 형식).

    data/final/
    ├── images/   <이름>.jpg   900장
    ├── labels/   <이름>.txt   900개
    ├── manifest_final.csv     (출처 Dataset / split 정보는 여기 남는다)
    └── final_file_map.csv     RAW 상대경로 -> FINAL 파일명

이미지는 원래 파일명을 그대로 쓴다. Dataset 1 과 2 에 같은 이름이 있을 때만
'<Dataset폴더>__<이름>' 으로 바꿔 겹치지 않게 한다.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath

from .dataset import ImageRecord


def final_stems(records: list[ImageRecord]) -> dict[str, str]:
    """rel_image -> FINAL 에서 쓸 파일 이름(확장자 제외)."""
    stems = {r.rel_image: PurePosixPath(r.rel_image).stem for r in records}
    dup = {s for s, n in Counter(stems.values()).items() if n > 1}
    for r in records:
        if stems[r.rel_image] in dup:
            stems[r.rel_image] = f"{r.source_dataset}__{stems[r.rel_image]}"
    return stems


def final_image_path(final_root: Path, rec: ImageRecord, stem: str) -> Path:
    return final_root / "images" / (stem + PurePosixPath(rec.rel_image).suffix.lower())


def final_label_path(final_root: Path, stem: str) -> Path:
    return final_root / "labels" / (stem + ".txt")
