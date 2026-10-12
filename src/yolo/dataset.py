"""RAW 폴더 구조 조사.

RAW 구조(원본 그대로 보존):
    <raw>/이물검출_학습데이터1/images/train/xxx.jpg
    <raw>/이물검출_학습데이터1/labels/train/xxx.txt
    <raw>/이물검출_학습데이터2/images/validation/yyy.jpg ...

이미지 하나를 구분하는 키는 파일명이 아니라 'RAW 기준 상대경로' 이다.
(Dataset 1 과 2 에 같은 파일명이 있어도 섞이지 않도록)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..config import IMAGE_EXTS, Paths


@dataclass
class ImageRecord:
    rel_image: str          # RAW 기준 이미지 상대경로 (posix)  <- 고유 키
    rel_label: str          # RAW 기준 라벨 상대경로 (posix)
    source_dataset: str
    original_split: str

    @property
    def image_name(self) -> str:
        return PurePosixPath(self.rel_image).name

    @property
    def label_name(self) -> str:
        return PurePosixPath(self.rel_label).name

    def _raw_rel(self, rel: str, paths: Paths) -> str:
        parts = PurePosixPath(rel).parts
        if parts and parts[0] == paths.raw.name:
            return str(PurePosixPath(*parts[1:]))
        return rel

    def raw_image(self, paths: Paths) -> Path:
        return paths.raw / self._raw_rel(self.rel_image, paths)

    def raw_label(self, paths: Paths) -> Path:
        return paths.raw / self._raw_rel(self.rel_label, paths)

    def work_label(self, paths: Paths) -> Path:
        # RAW 를 상위폴더로 열든 데이터1/2 폴더로 열든 같은 위치 (manifest 의 label_relative_path 와 동일)
        return paths.work / self.rel_label

    def legacy_work_labels(self, paths: Paths) -> list[Path]:
        """예전 버전(WORK/labels/...)에 저장된 위치 후보."""
        return [paths.work_labels / self.rel_label,
                paths.work_labels / self._raw_rel(self.rel_label, paths)]

    def effective_label(self, paths: Paths) -> Path:
        """WORK 에 저장본이 있으면 그것, 없으면 RAW 원본."""
        w = self.work_label(paths)
        return w if w.exists() else self.raw_label(paths)


def migrate_legacy_work(records: list["ImageRecord"], paths: Paths) -> int:
    """예전 WORK/labels/... 저장본을 새 위치로 복사한다 (원본은 지우지 않음, 새 위치에 이미 있으면 건드리지 않음)."""
    import shutil
    moved = 0
    for rec in records:
        new = rec.work_label(paths)
        if new.exists():
            continue
        for old in rec.legacy_work_labels(paths):
            if old.exists() and old != new:
                new.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old, new)
                moved += 1
                break
    return moved


def image_rel_to_label_rel(rel_image: str) -> tuple[str, str, str]:
    """이미지 상대경로 -> (라벨 상대경로, source_dataset, original_split)."""
    parts = list(PurePosixPath(rel_image).parts)
    stem_txt = str(PurePosixPath(parts[-1]).with_suffix(".txt"))
    if "images" in parts[:-1]:
        idx = len(parts) - 2 - parts[:-1][::-1].index("images")   # 마지막 'images'
        label_parts = parts[:idx] + ["labels"] + parts[idx + 1:-1] + [stem_txt]
        source = parts[idx - 1] if idx >= 1 else "root"
        split = parts[idx + 1] if idx + 1 < len(parts) - 1 else "unknown"
    else:   # images 폴더가 없으면 이미지 옆의 TXT
        label_parts = parts[:-1] + [stem_txt]
        source = parts[0] if len(parts) > 1 else "root"
        split = "unknown"
    return str(PurePosixPath(*label_parts)), source, split


def scan_images(raw_root: Path) -> list[ImageRecord]:
    if not raw_root.exists():
        raise FileNotFoundError(f"RAW 폴더가 없습니다: {raw_root}")
    records = []
    for p in sorted(raw_root.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and not p.name.startswith("."):
            rel = p.relative_to(raw_root).as_posix()
            if raw_root.name.startswith("이물검출_학습데이터") and not rel.startswith(f"{raw_root.name}/"):
                rel = f"{raw_root.name}/{rel}"
            rel_label, source, split = image_rel_to_label_rel(rel)
            records.append(ImageRecord(rel, rel_label, source, split))
    return records


def scan_orphan_labels(raw_root: Path, records: list[ImageRecord]) -> list[str]:
    """이미지 짝이 없는 TXT 목록 (classes.txt 같은 메타 파일 제외)."""
    expected = {r.rel_label for r in records}
    orphans = []
    for p in sorted(raw_root.rglob("*.txt")):
        rel = p.relative_to(raw_root).as_posix()
        if raw_root.name.startswith("이물검출_학습데이터") and not rel.startswith(f"{raw_root.name}/"):
            rel = f"{raw_root.name}/{rel}"
        if rel not in expected and p.name.lower() not in {"classes.txt", "readme.txt"}:
            orphans.append(rel)
    return orphans
