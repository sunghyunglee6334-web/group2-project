"""자동 Validation.

원칙: 자동으로 지우거나 고치지 않는다. 파일명과 오류 내용만 기록한다.

심각도
  CRITICAL : 반드시 0 이어야 FINAL 가능 (Pair, Parsing, Class 범위, 좌표 범위)
  REVIEW   : 사람이 판단 근거를 남겨야 함 (Class 4, 중복 의심, 아주 작은 BBox)
  INFO     : 확인용 (Empty Label 등)

검사 항목(CHECKS)은 결과 창 위쪽 체크리스트에 그대로 쓰인다.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field    ## , field 추가  / 10.13
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

###### 추가 ~   / 10.13
# 파싱된 좌표가 있어야만 다음 검사를 진행
LABEL_VALUE_CODES = (
    "CLASS_RANGE",
    "CLASS_4",
    "COORD_RANGE",
    "WH_ZERO",
    "BOX_OUTSIDE",
    "TINY_BOX",
    "DUPLICATE",
)

LABEL_CODES = ("PARSE", "EMPTY_LABEL", *LABEL_VALUE_CODES)

@dataclass
class ValidationCoverage:
    """검사별 수행 여부·생략·대상 없음 정보를 담는다."""

    checked: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    not_applicable: set[str] = field(default_factory=set)

    images_opened: int = 0
    labels_read: int = 0

    def mark(self, state: str, codes) -> None:
        getattr(self, state).update(codes)
#########   ~ 추가


def image_size(path: Path) -> tuple[int, int, int]:
    """(w, h, exif_orientation). 이미지 전체를 디코딩하지 않아 빠르다."""
    with Image.open(path) as im:
        orient = im.getexif().get(274, 1)
        return im.size[0], im.size[1], orient


def check_label_text(
    rel: str, 
    text: str, 
    img_w: int, 
    img_h: int,
    coverage: ValidationCoverage | None = None,) -> list[Issue]:    # coverage: ValidationCoverage | None = None, 추가
    issues: list[Issue] = []
    boxes = []

######   추가 ~ / 10.13
    if coverage is not None:
        coverage.mark("checked", ("PARSE", "EMPTY_LABEL"))

        if not text.strip():
            # 빈 TXT는 정상적인 입력이며, 좌표 검사 대상이 없다.
            coverage.mark("not_applicable", LABEL_VALUE_CODES)
######   ~ 추가


    for no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        val, err = parse_line(line)


######   수정   / 10.13
        if err:
            issues.append(Issue("CRITICAL", "PARSE", rel, no, err))
            if coverage is not None:
                coverage.mark("skipped", LABEL_VALUE_CODES)
            continue
        if coverage is not None:
            coverage.mark("checked", LABEL_VALUE_CODES)
        cls, cx, cy, w, h = val
######   수정    정상 행과 잘못된 행이 섞인 TXT도 일부 수행·일부 생략으로 기록하기 위한 코드 수정

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


# (화면 이름, 이 항목에 속하는 code 들). 순서대로 결과 창에 표시된다.
CHECKS = [
    ("TXT 형식", ("PARSE",)),
    ("Class ID 범위", ("CLASS_RANGE",)),
    ("좌표값 범위", ("COORD_RANGE",)),
    ("너비/높이", ("WH_ZERO",)),
    ("BBox 이미지 범위", ("BOX_OUTSIDE",)),
    ("파일 짝 확인", ("PAIR_NO_TXT", "PAIR_NO_JPG", "IMAGE_READ")),
    ("검수 상태", ("STATUS_REVIEW",)),
    ("기타 확인 (Class 4 · 중복 · 작은 BBox · EXIF)", ("CLASS_4", "DUPLICATE", "TINY_BOX", "EXIF_ROTATE")),
    ("빈 라벨 (BBox 없음)", ("EMPTY_LABEL",)),
    ("검사 대상", ("DATASET_EMPTY",)),              # 추가  / 10.13
    ("TXT 읽기", ("LABEL_READ",)),                 # 추가
]

SEVERITY_ORDER = {"CRITICAL": 0, "REVIEW": 1, "INFO": 2}

def status_issues(manifest, records: list[ImageRecord]) -> list[Issue]:
    """Manifest 에서 검수 상태가 REVIEW(확인 필요)인 이미지를 REVIEW 항목으로 만든다."""
    issues: list[Issue] = []
    for rec in records:
        row = manifest.rows.get(rec.rel_image)
        if not row or row["status"] != "REVIEW":
            continue
        reason = " / ".join(t for t in (row["issue"], row["note"]) if t.strip())
        msg = "검수 상태 '확인 필요'" + (f" - {reason}" if reason else "")
        issues.append(Issue("REVIEW", "STATUS_REVIEW", rec.rel_image, 0, msg))
    return issues


def validate(
    paths: Paths, 
    use_work: bool = True,
    records: list[ImageRecord] | None = None, 
    manifest=None,
    coverage: ValidationCoverage | None = None,             # coverage 추가 / 10.13
    require_work: bool = False,                         # WORK 라벨 검사 옵션 보완 / 10.18
) -> list[Issue]:
    """use_work=True 이면 WORK 저장본(없으면 RAW)을, False 이면 RAW 만 검사.
    manifest 를 주면 검수 상태가 REVIEW 인 이미지도 결과에 넣는다."""
    """ 수정 : 데이터 문제 목록을 반환하고, 선택적으로 검사 수행 정보를 기록한다."""

    records = records if records is not None else scan_images(paths.raw)
    coverage = coverage if coverage is not None else ValidationCoverage()   # coverage 추가 / 10.13
    issues: list[Issue] = []

# coverage 추가 ~
    if not records:                 
        issues.append(
            Issue(
                "CRITICAL",
                "DATASET_EMPTY",
                "",
                0,
                "검사할 이미지가 없습니다. RAW 경로를 확인하세요.",
            )
        )                           
#######   ~ 추가             # WORK 라벨 검사 옵션 보완 / 10.18
    for rec in records:
        img_path = rec.raw_image(paths)

        if not use_work:
            label_path = rec.raw_label(paths)
        elif require_work:
            label_path = rec.work_label(paths)
        else:
            label_path = rec.effective_label(paths)
# ~ 수정        
        coverage.mark("checked", ("IMAGE_READ",))   # 추가  / 10.13
        
        try:
            w, h, orient = image_size(img_path)
        except Exception as e:
            issues.append(Issue("CRITICAL", "IMAGE_READ", rec.rel_image, 0, f"이미지 열기 실패: {e}"))
            coverage.mark(              ##### coverage 관련 추가 ~~~    / 10.13
                "skipped",
                ("PAIR_NO_TXT", "EXIF_ROTATE", *LABEL_CODES),
            )                           # ~~~~~ 추가 
            continue

        coverage.images_opened += 1             # coverage 관련 추가    / 10.13
        coverage.mark("checked", ("EXIF_ROTATE", "PAIR_NO_TXT"))

        if orient not in (0, 1):
            issues.append(Issue("REVIEW", "EXIF_ROTATE", rec.rel_image, 0,
                                f"EXIF 회전값 {orient} - 화면 방향과 좌표가 다를 수 있음"))
        if not label_path.exists():
            issues.append(Issue("CRITICAL", "PAIR_NO_TXT", rec.rel_image, 0, "이미지는 있는데 TXT 없음"))
            coverage.mark("skipped", LABEL_CODES)           # coverage 관련 추가    / 10.13
            continue

### coverage 관련 수정  ~~~   / 10.13
        coverage.mark("checked", ("LABEL_READ",))            
        try:
            text = label_path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )
        except OSError as e:
            issues.append(
                Issue(
                    "CRITICAL",
                    "LABEL_READ",
                    rec.rel_image,
                    0,
                    f"TXT 읽기 실패: {e}",
                )
            )
            coverage.mark("skipped", LABEL_CODES)
            continue

        coverage.labels_read += 1
        issues.extend(
            check_label_text(
                rec.rel_image,
                text,
                w,
                h,
                coverage=coverage,
            )
        )

    for orphan in scan_orphan_labels(paths.raw, records):
        issues.append(
            Issue(
                "CRITICAL",
                "PAIR_NO_JPG",
                orphan,
                0,
                "TXT는 있는데 이미지 없음",
            )
        )
    coverage.mark("checked", ("PAIR_NO_JPG", "DATASET_EMPTY"))

    if manifest is not None:
        issues.extend(status_issues(manifest, records))
        coverage.mark("checked", ("STATUS_REVIEW",))
    else:
        # Manifest가 없으면 검수 상태는 검사하지 않았다.
        coverage.mark("skipped", ("STATUS_REVIEW",))

    issues.sort(key=lambda i: SEVERITY_ORDER.get(i.severity, 9))
    return issues                                                 
###             ~~~~     수정 
# 02_validate.py도 같은 validate()를 사용하므로, 
# 이제 빈 이미지 폴더는 CRITICAL로 보고되고 종료코드가 1이 되도록 수정.


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
