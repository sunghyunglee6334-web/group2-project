"""이미지 Canvas 위에 직접 그리는 떠 있는 UI: Zoom 막대, 미니맵, 배율 토스트.

Tk 위젯은 투명하게 만들 수 없어서 이미지 위에 올리면 네모난 바탕이 보인다.
그래서 Canvas 도형(둥근 사각형 + 글자)으로 직접 그려 이미지 위에 깔끔하게 띄운다.
모든 도형은 'overlay' 태그를 달고, BBox 보다 항상 위에 있다.

    [ −   50%   + │ 맞춤   100% ]        (아래 가운데)
                                 [미니맵]  (오른쪽 아래, 확대했을 때만)
              ┌──────┐
              │ 150% │                     (가운데, 배율이 바뀔 때 잠깐)
              └──────┘
"""
import math

from PIL import ImageTk

from .style import BLUE, BLUE_SOFT, CARD, FILL, FONT_BOLD, FONT_LARGE, FONT_SMALL_BOLD, FONT_TOAST, LINE, TEXT, TEXT2
from .widgets import round_rect

# 토스 스타일: 어두운 이미지 위에 흰 알약
HUD_BG = "#FFFFFF"
HUD_LINE = LINE
HUD_HOVER = FILL
HUD_TEXT = TEXT
HUD_SUB = TEXT2
HUD_ON = BLUE
HUD_ON_BG = BLUE_SOFT
STAGE_RADIUS = 16       # 이미지 무대의 둥근 모서리

HUD_W, HUD_H = 300, 44
HUD_GAP = 16            # 캔버스 아래쪽과의 간격
MAP_MAX_W, MAP_MAX_H = 210, 140
TOAST_MS = 650

# (키, 왼쪽 x, 오른쪽 x)  HUD 안 좌표
HUD_ITEMS = [("out", 6, 44), ("pct", 44, 112), ("in", 112, 150), ("fit", 160, 226), ("actual", 228, 294)]


def shows_all(view, canvas_w, canvas_h):
    """이미지 전체가 화면 안에 다 보이는가 (그러면 미니맵이 필요 없다)."""
    x1, y1 = view.to_canvas(0, 0)
    x2, y2 = view.to_canvas(view.img_w, view.img_h)
    return x1 >= -1 and y1 >= -1 and x2 <= canvas_w + 1 and y2 <= canvas_h + 1


class CanvasOverlay:
    def __init__(self, app):
        self.app = app
        self.c = app.canvas
        self.hover = None
        self.hud_box = None         # (x1, y1, x2, y2) 캔버스 좌표
        self.map_box = None
        self.map_photo = None
        self.map_scale = 1.0
        self.map_size = (0, 0)
        self.toast_text = None
        self.toast_job = None
        self.visible = True

    # ---------------------------------------------------------------- 그리기
    def set_map_image(self, pil_img, full_size):
        """pil_img: 작게 줄인 이미지, full_size: 원본 (w, h). 미니맵 배율은 원본 기준."""
        w, h = full_size
        self.map_scale = min(MAP_MAX_W / w, MAP_MAX_H / h)
        tw, th = max(1, round(w * self.map_scale)), max(1, round(h * self.map_scale))
        self.map_size = (tw, th)
        self.map_photo = ImageTk.PhotoImage(pil_img.resize((tw, th)))

    def draw(self, visible_rect=None):
        c = self.c
        c.delete("overlay")
        self.hud_box = self.map_box = None
        cw, ch = c.winfo_width(), c.winfo_height()
        if not self.visible:
            self._draw_corners(cw, ch)
            return
        self._draw_hud(cw, ch)
        view = self.app.view
        if visible_rect is not None and self.map_photo and not shows_all(view, cw, ch):
            self._draw_map(cw, ch, visible_rect)
        if self.toast_text:
            self._draw_toast(cw, ch)
        self._draw_corners(cw, ch)
        c.tag_raise("overlay")

    def _draw_corners(self, cw, ch):
        """캔버스 네 모서리를 카드 색으로 덮어서 둥글게 보이게 한다."""
        r = STAGE_RADIUS
        for (x, y, a0) in ((0, 0, 180), (cw, 0, 270), (cw, ch, 0), (0, ch, 90)):
            # 모서리 꼭짓점 + 사분원 호
            cx = x + (r if x == 0 else -r)
            cy = y + (r if y == 0 else -r)
            pts = [x, y]
            for k in range(0, 91, 10):
                t = math.radians(a0 + k)
                pts += [cx + r * math.cos(t), cy + r * math.sin(t)]
            self.c.create_polygon(pts, fill=CARD, outline=CARD, tags="overlay")

    def _draw_hud(self, cw, ch):
        c = self.c
        x0 = (cw - HUD_W) / 2
        y0 = ch - HUD_GAP - HUD_H
        self.hud_box = (x0, y0, x0 + HUD_W, y0 + HUD_H)
        round_rect(c, x0, y0, x0 + HUD_W, y0 + HUD_H, HUD_H / 2, fill=HUD_BG, outline=HUD_BG,
                   tags="overlay")
        fit_on = self.app.fit_mode
        actual_on = abs(self.app.view.scale - 1) < 1e-6
        texts = {
            "out": ("−", FONT_LARGE, HUD_TEXT),
            "pct": (self.app.percent_text(), FONT_BOLD, HUD_TEXT),
            "in": ("+", FONT_LARGE, HUD_TEXT),
            "fit": ("맞춤", FONT_SMALL_BOLD, HUD_ON if fit_on else HUD_SUB),
            "actual": ("100%", FONT_SMALL_BOLD, HUD_ON if actual_on else HUD_SUB),
        }
        on = {"fit": fit_on, "actual": actual_on}
        for key, x1, x2 in HUD_ITEMS:
            bg = HUD_ON_BG if on.get(key) else (HUD_HOVER if key == self.hover and key != "pct" else None)
            if bg:
                round_rect(c, x0 + x1, y0 + 6, x0 + x2, y0 + HUD_H - 6, 16, fill=bg, outline=bg,
                           tags="overlay")
            text, font, color = texts[key]
            c.create_text(x0 + (x1 + x2) / 2, y0 + HUD_H / 2, text=text, font=font, fill=color,
                          tags="overlay")
        c.create_line(x0 + 155, y0 + 11, x0 + 155, y0 + HUD_H - 11, fill=HUD_LINE, tags="overlay")

    def _draw_map(self, cw, ch, rect):
        c = self.c
        tw, th = self.map_size
        x0 = cw - 16 - tw
        y0 = ch - HUD_GAP - th
        self.map_box = (x0, y0, x0 + tw, y0 + th)
        round_rect(c, x0 - 4, y0 - 4, x0 + tw + 4, y0 + th + 4, 12, fill=HUD_BG, outline=HUD_BG,
                   tags="overlay")
        c.create_image(x0, y0, image=self.map_photo, anchor="nw", tags="overlay")
        s = self.map_scale
        x1, y1, x2, y2 = rect
        box = (x0 + x1 * s, y0 + y1 * s, x0 + x2 * s, y0 + y2 * s)
        c.create_rectangle(*box, outline="white", width=4, tags="overlay")
        c.create_rectangle(*box, outline=HUD_ON, width=2, tags="overlay")

    def _draw_toast(self, cw, ch):
        c = self.c
        tid = c.create_text(cw / 2, ch / 2, text=self.toast_text, font=FONT_TOAST, fill=HUD_TEXT,
                            tags="overlay")
        x1, y1, x2, y2 = c.bbox(tid)
        bg = round_rect(c, x1 - 24, y1 - 10, x2 + 24, y2 + 10, 18, fill=HUD_BG, outline=HUD_BG,
                        tags="overlay")
        c.tag_lower(bg, tid)

    def redraw(self):
        """이미지는 그대로 두고 떠 있는 UI 만 다시 그린다 (마우스 hover 등)."""
        c = self.c
        rect = self.app.view.visible_image_rect(c.winfo_width(), c.winfo_height()) if self.app.pyramid else None
        self.draw(rect)

    def toast(self, text):
        self.toast_text = text
        if self.toast_job:
            self.c.after_cancel(self.toast_job)
        self.toast_job = self.c.after(TOAST_MS, self._end_toast)

    def _end_toast(self):
        self.toast_job = None
        self.toast_text = None
        self.redraw()

    # ---------------------------------------------------------------- 마우스
    @staticmethod
    def _inside(box, x, y):
        return box is not None and box[0] <= x <= box[2] and box[1] <= y <= box[3]

    def hit(self, x, y):
        """(x, y) 가 떠 있는 UI 위면 'hud' / 'map', 아니면 None."""
        if self._inside(self.hud_box, x, y):
            return "hud"
        if self._inside(self.map_box, x, y):
            return "map"
        return None

    def hud_key(self, x):
        x0 = self.hud_box[0]
        for key, x1, x2 in HUD_ITEMS:
            if x0 + x1 <= x <= x0 + x2:
                return key
        return None

    def on_motion(self, x, y):
        """마우스가 떠 있는 UI 위에 있으면 True (그리기 십자선 등을 생략)."""
        part = self.hit(x, y)
        key = self.hud_key(x) if part == "hud" else None
        if key != self.hover:
            self.hover = key
            self.redraw()
        if part:
            self.c.configure(cursor="hand2" if (part == "map" or (key and key != "pct")) else "arrow")
            self.c.delete("cross")
            return True
        return False

    def click(self, x, y):
        part = self.hit(x, y)
        if part == "hud":
            action = {"out": self.app.zoom_out, "in": self.app.zoom_in, "fit": self.app.fit,
                      "actual": self.app.zoom_actual}.get(self.hud_key(x))
            if action:
                action()
        elif part == "map":
            self.map_jump(x, y)

    def map_jump(self, x, y):
        if self.map_box is None:
            return
        x0, y0, x1, y1 = self.map_box
        mx = min(max(x, x0), x1) - x0
        my = min(max(y, y0), y1) - y0
        self.app.jump_view(mx / self.map_scale, my / self.map_scale)
