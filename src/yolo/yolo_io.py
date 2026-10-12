"""YOLO TXT 읽기/쓰기와 좌표 변환.

좌표 원칙
  - TXT 안   : YOLO 정규화 좌표  (class cx cy w h, 0~1)
  - 프로그램 안: '원본 이미지 픽셀' 좌표 (x1, y1, x2, y2)  <- BBox 상태는 항상 이것
  - 화면     : view.py 의 ViewTransform 이 원본 픽셀 <-> 캔버스 픽셀 변환
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Box:
    """원본 이미지 픽셀 좌표 BBox."""
    cls: int
    x1: float
    y1: float
    x2: float
    y2: float

    def normalized(self) -> "Box":
        """x1<x2, y1<y2 가 되도록 정렬한 복사본."""
        return Box(self.cls, min(self.x1, self.x2), min(self.y1, self.y2),
                   max(self.x1, self.x2), max(self.y1, self.y2))

    @property
    def w(self) -> float:
        return abs(self.x2 - self.x1)

    @property
    def h(self) -> float:
        return abs(self.y2 - self.y1)

    def contains(self, x: float, y: float) -> bool:
        b = self.normalized()
        return b.x1 <= x <= b.x2 and b.y1 <= y <= b.y2

    def clamp(self, img_w: int, img_h: int) -> "Box":
        b = self.normalized()
        return Box(b.cls, max(0.0, min(b.x1, img_w)), max(0.0, min(b.y1, img_h)),
                   max(0.0, min(b.x2, img_w)), max(0.0, min(b.y2, img_h)))


@dataclass
class ParseResult:
    boxes: list[Box] = field(default_factory=list)   # 정상 파싱된 BBox (픽셀)
    errors: list[str] = field(default_factory=list)  # 사람이 읽을 오류 메시지
    raw_lines: list[str] = field(default_factory=list)  # 원본 줄 (빈 줄 제외)


# ---------------------------------------------------------------- 변환
def yolo_to_pixel(cls: int, cx: float, cy: float, w: float, h: float,
                  img_w: int, img_h: int) -> Box:
    x1 = (cx - w / 2.0) * img_w
    y1 = (cy - h / 2.0) * img_h
    x2 = (cx + w / 2.0) * img_w
    y2 = (cy + h / 2.0) * img_h
    return Box(cls, x1, y1, x2, y2)


def pixel_to_yolo(box: Box, img_w: int, img_h: int) -> tuple[int, float, float, float, float]:
    b = box.normalized()
    cx = (b.x1 + b.x2) / 2.0 / img_w
    cy = (b.y1 + b.y2) / 2.0 / img_h
    w = (b.x2 - b.x1) / img_w
    h = (b.y2 - b.y1) / img_h
    return b.cls, cx, cy, w, h


def format_line(cls: int, cx: float, cy: float, w: float, h: float) -> str:
    return f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


# ---------------------------------------------------------------- 파싱
def parse_line(line: str) -> tuple[tuple[int, float, float, float, float] | None, str | None]:
    """한 줄 -> (값, None) 또는 (None, 오류메시지)."""
    parts = line.split()
    if len(parts) != 5:
        return None, f"값 개수 {len(parts)}개 (5개여야 함)"
    try:
        cls_f = float(parts[0])
    except ValueError:
        return None, f"class 숫자 변환 실패 '{parts[0]}'"
    if not cls_f.is_integer():
        return None, f"class 가 정수가 아님 '{parts[0]}'"
    try:
        cx, cy, w, h = (float(p) for p in parts[1:])
    except ValueError:
        return None, "좌표 숫자 변환 실패"
    return (int(cls_f), cx, cy, w, h), None


def parse_label_text(text: str, img_w: int, img_h: int) -> ParseResult:
    res = ParseResult()
    for no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        res.raw_lines.append(line.strip())
        val, err = parse_line(line)
        if err:
            res.errors.append(f"{no}번째 줄: {err}")
            continue
        res.boxes.append(yolo_to_pixel(*val, img_w, img_h))
    return res


def read_label_file(path: Path, img_w: int, img_h: int) -> ParseResult:
    if not path.exists():
        r = ParseResult()
        r.errors.append("TXT 파일 없음")
        return r
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return parse_label_text(text, img_w, img_h)


def boxes_to_text(boxes: list[Box], img_w: int, img_h: int) -> str:
    lines = [format_line(*pixel_to_yolo(b, img_w, img_h)) for b in boxes]
    return "\n".join(lines) + ("\n" if lines else "")


def atomic_write_text(path: Path, text: str) -> None:
    """임시파일에 먼저 쓰고 교체 -> 저장 도중 꺼져도 TXT 가 깨지지 않는다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def atomic_copy(src: Path, dst: Path) -> None:
    """파일을 바이트 그대로 복사 (줄바꿈 CRLF/BOM 까지 보존). 임시파일 -> 교체."""
    data = Path(src).read_bytes()
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dst.parent), prefix=".tmp_", suffix=dst.suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, dst)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def iou(a: Box, b: Box) -> float:
    a, b = a.normalized(), b.normalized()
    ix = max(0.0, min(a.x2, b.x2) - max(a.x1, b.x1))
    iy = max(0.0, min(a.y2, b.y2) - max(a.y1, b.y1))
    inter = ix * iy
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0
