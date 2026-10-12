"""화면 좌표 <-> 원본 이미지 좌표 변환.

    canvas_x = image_x * scale + offset_x
    image_x  = (canvas_x - offset_x) / scale

BBox 는 항상 원본 좌표로 저장하고, 화면에 그릴 때만 변환한다.
그래서 Zoom/Pan 을 아무리 해도 BBox 의 실제 위치는 변하지 않는다.
"""
from __future__ import annotations

MIN_SCALE = 0.02
MAX_SCALE = 16.0


class ViewTransform:
    def __init__(self) -> None:
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.img_w = 1
        self.img_h = 1

    # --------------------------------------------------- 변환
    def to_canvas(self, x: float, y: float) -> tuple[float, float]:
        return x * self.scale + self.offset_x, y * self.scale + self.offset_y

    def to_image(self, cx: float, cy: float) -> tuple[float, float]:
        return (cx - self.offset_x) / self.scale, (cy - self.offset_y) / self.scale

    # --------------------------------------------------- 조작
    def fit(self, img_w: int, img_h: int, canvas_w: int, canvas_h: int, margin: int = 10) -> None:
        """이미지 전체가 캔버스에 들어오도록 맞춘다 (Fit to Window)."""
        self.img_w, self.img_h = img_w, img_h
        cw, ch = max(canvas_w - 2 * margin, 1), max(canvas_h - 2 * margin, 1)
        self.scale = max(MIN_SCALE, min(cw / img_w, ch / img_h))
        self.offset_x = (canvas_w - img_w * self.scale) / 2.0
        self.offset_y = (canvas_h - img_h * self.scale) / 2.0

    def zoom_at(self, factor: float, cx: float, cy: float) -> None:
        """캔버스 점 (cx, cy) 아래의 이미지 위치가 그대로 유지되도록 확대/축소."""
        ix, iy = self.to_image(cx, cy)
        new_scale = max(MIN_SCALE, min(MAX_SCALE, self.scale * factor))
        self.scale = new_scale
        self.offset_x = cx - ix * new_scale
        self.offset_y = cy - iy * new_scale

    def pan(self, dx: float, dy: float) -> None:
        self.offset_x += dx
        self.offset_y += dy

    def visible_image_rect(self, canvas_w: int, canvas_h: int) -> tuple[int, int, int, int] | None:
        """캔버스에 보이는 원본 이미지 영역 (정수 픽셀, 이미지 범위로 자름)."""
        x1, y1 = self.to_image(0, 0)
        x2, y2 = self.to_image(canvas_w, canvas_h)
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(self.img_w, int(x2) + 1), min(self.img_h, int(y2) + 1)
        if x2 <= x1 or y2 <= y1:
            return None
        return x1, y1, x2, y2
