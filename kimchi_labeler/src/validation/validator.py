"""자동 Validation.

원칙: 자동으로 지우거나 고치지 않는다. 파일명과 오류 내용만 기록한다.

심각도
  CRITICAL : 반드시 0 이어야 FINAL 가능 (Pair, Parsing, Class 범위, 좌표 범위)
  REVIEW   : 사람이 판단 근거를 남겨야 함 (Class 4, 중복 의심, 아주 작은 BBox)
  INFO     : 확인용 (Empty Label 등)
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ..config import (DUP_IOU_THRESHOLD, MIN_BOX_PX, UNUSED_CLASS_IDS, VALID_CLASS_IDS,
                      Paths)
from ..yolo.dataset import ImageRecord, scan_images, scan_orphan_labels
from ..yolo.yolo_io import iou, parse_line, yolo_to_pixel

EPS = 1e-6


@dataclass
class Issue:
    severity: str
    code: str
    rel_path: str
    line: int
    message: str


def image_size(path: Path) -> tuple[int, int, int]:
    """(w, h, exif_orientation). 이미지 전체를 디코딩하지 않아 빠르다."""
    with Image.open(path) as im:
        orient = im.getexif().get(274, 1)
        return im.size[0], im.size[1], orient


def check_label_text(rel: str, text: str, img_w: int, img_h: int) -> list[Issue]:
    issues: list[Issue] = []
    boxes = []
    for no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        val, err = parse_line(line)
        if err:
            issues.append(Issue("CRITICAL", "PARSE", rel, no, err))
            continue
        cls, cx, cy, w, h = val
        if cls not in VALID_CLASS_IDS:
            issues.append(Issue("CRITICAL", "CLASS_RANGE", rel, no, f"Class {cls} 는 0~6 범위 밖"))
        elif cls in UNUSED_CLASS_IDS:
            issues.append(Issue("REVIEW", "CLASS_4", rel, no, "Class 4(고무장갑, 미사용) 발견 -> REVIEW"))
        if not all(0 - EPS <= v <= 1 + EPS for v in (cx, cy, w, h)):
            issues.append(Issue("CRITICAL", "COORD_RANGE", rel, no, f"좌표가 0~1 밖 ({cx},{cy},{w},{h})"))
        if w <= 0 or h <= 0:
            issues.append(Issue("CRITICAL", "WH_ZERO", rel, no, f"너비/높이가 0 이하 (w={w}, h={h})"))
        if (cx - w / 2 < -EPS or cy - h / 2 < -EPS or cx + w / 2 > 1 + EPS or cy + h / 2 > 1 + EPS):
            issues.append(Issue("CRITICAL", "BOX_OUTSIDE", rel, no, "BBox 가 이미지 경계를 벗어남"))
        b = yolo_to_pixel(cls, cx, cy, w, h, img_w, img_h)
        if 0 < b.w < MIN_BOX_PX or 0 < b.h < MIN_BOX_PX:
            issues.append(Issue("REVIEW", "TINY_BOX", rel, no, f"아주 작은 BBox ({b.w:.1f}x{b.h:.1f}px)"))
        for pno, prev in boxes:
            if prev.cls == b.cls and iou(prev, b) >= DUP_IOU_THRESHOLD:
                issues.append(Issue("REVIEW", "DUPLICATE", rel, no, f"{pno}번째 줄과 중복 의심 (IoU>={DUP_IOU_THRESHOLD})"))
        boxes.append((no, b))
    if not boxes and not issues:
        issues.append(Issue("INFO", "EMPTY_LABEL", rel, 0, "BBox 없음 - 정상 이미지인지 사람이 확인"))
    return issues


def validate(paths: Paths, use_work: bool = True,
             records: list[ImageRecord] | None = None) -> list[Issue]:
    """use_work=True 이면 WORK 저장본(없으면 RAW)을, False 이면 RAW 만 검사."""
    records = records if records is not None else scan_images(paths.raw)
    issues: list[Issue] = []
    for rec in records:
        img_path = rec.raw_image(paths)
        label_path = rec.effective_label(paths) if use_work else rec.raw_label(paths)
        try:
            w, h, orient = image_size(img_path)
        except Exception as e:
            issues.append(Issue("CRITICAL", "IMAGE_READ", rec.rel_image, 0, f"이미지 열기 실패: {e}"))
            continue
        if orient not in (0, 1):
            issues.append(Issue("REVIEW", "EXIF_ROTATE", rec.rel_image, 0,
                                f"EXIF 회전값 {orient} - 화면 방향과 좌표가 다를 수 있음"))
        if not label_path.exists():
            issues.append(Issue("CRITICAL", "PAIR_NO_TXT", rec.rel_image, 0, "JPG 는 있는데 TXT 없음"))
            continue
        text = label_path.read_text(encoding="utf-8-sig", errors="replace")
        issues.extend(check_label_text(rec.rel_image, text, w, h))
    for orphan in scan_orphan_labels(paths.raw, records):
        issues.append(Issue("CRITICAL", "PAIR_NO_JPG", orphan, 0, "TXT 는 있는데 JPG 없음"))
    return issues


def summarize(issues: list[Issue]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for i in issues:
        out.setdefault(i.severity, {}).setdefault(i.code, 0)
        out[i.severity][i.code] += 1
    return out


def write_report(issues: list[Issue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["severity", "code", "relative_path", "line", "message"])
        for i in issues:
            w.writerow([i.severity, i.code, i.rel_path, i.line, i.message])


def critical_count(issues: list[Issue]) -> int:
    return sum(1 for i in issues if i.severity == "CRITICAL")
