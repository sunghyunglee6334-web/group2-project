"""Canvas 위의 이미지와 BBox 그리기, 마우스 편집.

BBox 는 항상 원본 이미지 픽셀 좌표로 들고 있고, 그릴 때만 화면 좌표로 바꾼다.
    화면 = 원본 * scale + offset         (view.to_canvas)
    원본 = (화면 - offset) / scale       (view.to_image)

마우스를 누르는 순간 무엇을 할지 정해서 self.drag 에 담아 둔다.
    draw   : 빈 곳을 드래그해서 새 BBox
    move   : 선택 이동 모드에서 BBox 안을 드래그
    resize : 선택된 BBox 의 흰 핸들을 드래그
드래그 중(on_left_drag)과 놓을 때(on_left_up)는 drag["kind"] 만 보고 움직인다.
"""
from tkinter import messagebox

from PIL import Image, ImageTk

from ..config import ACTIVE_CLASS_IDS, CLASS_COLORS, CLASS_NAMES, UNUSED_CLASS_IDS
from ..ui.style import FONT_BOX, FONT_SMALL_BOLD, HANDLE_CURSORS, HANDLE_RADIUS, MODE_CURSORS, text_on
from ..yolo.yolo_io import Box

DRAG_START_PX = 3       # 이보다 적게 움직이면 클릭으로 본다
CLICK_PX = 4            # 새 BBox 모드에서 이보다 짧게 끌면 'BBox 선택' 클릭
HUD_SPACE = 64          # Fit 할 때 아래쪽 Zoom 막대 자리로 비워 둘 높이

# Zoom 막대의 + / − 버튼이 거치는 배율 (보기 좋은 숫자로 끊어서)
ZOOM_STEPS = [0.05, 0.0625, 0.08, 0.1, 0.125, 0.15, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75,
              1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0]


class CanvasEditor:
    """LabelApp 이 상속해서 쓴다. self.canvas, self.view, self.s 가 있어야 한다."""

    # ---- Canvas 이벤트 연결
    def bind_canvas(self):
        c = self.canvas
        c.bind("<Configure>", self.on_resize)

        c.bind("<ButtonPress-1>", self.on_left_down)
        c.bind("<B1-Motion>", self.on_left_drag)
        c.bind("<ButtonRelease-1>", self.on_left_up)

        # 오른쪽/가운데 버튼 드래그는 어느 모드에서나 화면 이동
        for button in ("2", "3"):
            c.bind(f"<ButtonPress-{button}>", self.on_pan_start)
            c.bind(f"<B{button}-Motion>", self.on_pan_drag)
            c.bind(f"<ButtonRelease-{button}>", self.on_pan_end)

        c.bind("<MouseWheel>", self.on_wheel)                       # Windows / macOS
        c.bind("<Button-4>", lambda e: self.zoom_at(1.25, e.x, e.y))  # Linux 휠 위
        c.bind("<Button-5>", lambda e: self.zoom_at(0.8, e.x, e.y))   # Linux 휠 아래

        c.bind("<Motion>", self.on_motion)
        c.bind("<Leave>", lambda e: c.delete("cross"))

    # ---- 확대 / 축소
    def fit(self):
        if not self.pyramid:
            return
        width, height = self.pyramid[0].size
        # 아래쪽 Zoom 막대 자리(HUD_SPACE)를 비워 두고 맞춘다
        self.view.fit(width, height, self.canvas.winfo_width(),
                      max(1, self.canvas.winfo_height() - HUD_SPACE), margin=16)
        self.fit_mode = True
        self.render()

    def zoom_at(self, factor, x, y):
        if not self.pyramid:
            return
        self.view.zoom_at(factor, x, y)
        self.fit_mode = False
        self.render()

    def zoom_center(self, factor):
        """Zoom In / Out: 한 단계씩 (25 → 33 → 50 → 67 → 75 → 100 → 125 ...%), 가운데에 배율을 크게 표시."""
        if not self.pyramid:
            return
        scale = self.view.scale
        if factor > 1:
            target = next((z for z in ZOOM_STEPS if z > scale * 1.01), ZOOM_STEPS[-1])
        else:
            target = next((z for z in reversed(ZOOM_STEPS) if z < scale * 0.99), ZOOM_STEPS[0])
        self.zoom_to(target)

    def zoom_to(self, scale):
        self.overlay.toast(f"{scale * 100:.0f}%" if scale >= 0.1 else f"{scale * 100:.1f}%")
        self.zoom_at(scale / self.view.scale, self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)

    def zoom_in(self):
        self.zoom_center(1.25)

    def zoom_out(self):
        self.zoom_center(0.8)

    def zoom_actual(self):
        """100% = 원본 픽셀 1개가 화면 픽셀 1개."""
        if self.pyramid:
            self.zoom_to(1.0)

    def percent_text(self):
        p = self.view.scale * 100
        return f"{p:.0f}%" if p >= 10 else f"{p:.1f}%"

    def jump_view(self, ix, iy):
        """미니맵을 누르면 그 위치가 화면 가운데로 오게 이동."""
        v = self.view
        v.pan(self.canvas.winfo_width() / 2 - (ix * v.scale + v.offset_x),
              self.canvas.winfo_height() / 2 - (iy * v.scale + v.offset_y))
        self.fit_mode = False
        self.render()

    def on_wheel(self, event):
        self.zoom_at(1.25 if event.delta > 0 else 0.8, event.x, event.y)

    def on_resize(self, _event):
        if not self.pyramid:
            self.overlay.draw()          # 이미지가 없어도 둥근 모서리는 다시 그린다
            return
        if self.fit_mode:
            self.fit()
        else:
            self.render()

    # ---- 이미지 그리기
    def make_pyramid(self, img):
        """4K 를 빠르게 그리려고 원본, 1/2, 1/4 크기를 미리 만들어 둔다."""
        self.pyramid = [img]
        for _ in range(2):
            src = self.pyramid[-1]
            if min(src.size) < 400:
                break
            self.pyramid.append(src.reduce(2))
        self.overlay.set_map_image(self.pyramid[-1], img.size)

    def render(self):
        c = self.canvas
        c.delete("all")
        if not self.pyramid or not self.s.cur:
            return

        rect = self.view.visible_image_rect(c.winfo_width(), c.winfo_height())
        if rect:
            x1, y1, x2, y2 = rect

            # 축소해서 볼 때는 작은 이미지를 쓴다.
            level = 0
            while level + 1 < len(self.pyramid) and self.view.scale <= 0.5 ** (level + 1):
                level += 1
            f = 2 ** level

            # 화면에 보이는 부분만 잘라서 확대/축소한다.
            src = self.pyramid[level]
            crop = src.crop((x1 // f, y1 // f,
                             max(x2 // f, x1 // f + 1), max(y2 // f, y1 // f + 1)))
            dw = max(1, round((x2 - x1) * self.view.scale))
            dh = max(1, round((y2 - y1) * self.view.scale))
            resample = Image.NEAREST if self.view.scale >= 2 else Image.BILINEAR

            # PhotoImage 는 변수로 잡고 있지 않으면 사라진다 -> self.photo 에 보관
            self.photo = ImageTk.PhotoImage(crop.resize((dw, dh), resample))
            px, py = self.view.to_canvas(x1, y1)
            c.create_image(px, py, image=self.photo, anchor="nw")

        self.draw_boxes()
        self.zoom_var.set(f"배율 {self.view.scale * 100:.0f}%")
        self.overlay.draw(rect)          # Zoom 막대 · 미니맵 · 배율 표시 · 둥근 모서리

    # ---- BBox 그리기
    def handles(self, box):
        x1, y1 = self.view.to_canvas(box.x1, box.y1)
        x2, y2 = self.view.to_canvas(box.x2, box.y2)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        return {
            "nw": (x1, y1), "n": (mx, y1), "ne": (x2, y1),
            "w": (x1, my), "e": (x2, my),
            "sw": (x1, y2), "s": (mx, y2), "se": (x2, y2),
        }

    def hit_handle(self, x, y):
        if self.selected is None or not self.s.cur or self.hide_labels:
            return None
        for name, (hx, hy) in self.handles(self.s.cur.boxes[self.selected]).items():
            if abs(x - hx) <= HANDLE_RADIUS and abs(y - hy) <= HANDLE_RADIUS:
                return name
        return None

    def draw_boxes(self):
        c = self.canvas
        c.delete("box")
        cur = self.s.cur
        if not cur:
            return

        if self.selected is not None and self.selected >= len(cur.boxes):
            self.selected = None

        if self.hide_labels:
            c.create_text(18, 18, text="라벨 숨김 · H 로 다시 보기", anchor="nw",
                          fill="#FFD60A", font=FONT_SMALL_BOLD, tags="box")
        else:
            for i, box in enumerate(cur.boxes):
                self._draw_one_box(i, box)

        c.tag_raise("overlay")          # Zoom 막대·미니맵은 항상 BBox 위
        self.refresh_box_list()
        self.refresh_box_info()

    def _draw_one_box(self, i, box):
        c = self.canvas
        x1, y1 = self.view.to_canvas(box.x1, box.y1)
        x2, y2 = self.view.to_canvas(box.x2, box.y2)
        color = CLASS_COLORS.get(box.cls, "#ff0000")
        selected = i == self.selected

        # 사용하지 않는 Class(4)와 범위 밖 Class 는 점선
        dash = None
        if box.cls in UNUSED_CLASS_IDS or box.cls not in CLASS_NAMES:
            dash = (6, 3)

        if selected:
            c.create_rectangle(x1 - 2, y1 - 2, x2 + 2, y2 + 2, outline="white", width=1, tags="box")
        c.create_rectangle(x1, y1, x2, y2, outline=color, width=4 if selected else 2,
                           dash=dash, tags="box")

        # Class 이름표: 위에 공간이 없으면 BBox 안쪽에 붙인다. 밝은 색(노랑 등)이면 검은 글자.
        label = f"{box.cls}  {CLASS_NAMES.get(box.cls, '?')}"
        ty = y1 - 21 if y1 > 23 else y1 + 2
        text_id = c.create_text(x1 + 7, ty + 10, text=label, anchor="w", fill=text_on(color),
                                font=FONT_BOX, tags="box")
        right = c.bbox(text_id)[2]
        bg_id = c.create_rectangle(x1 - (1 if selected else 0), ty, right + 7, ty + 20, fill=color,
                                   outline="", tags="box")
        c.tag_lower(bg_id, text_id)

        if selected:
            for hx, hy in self.handles(box).values():
                c.create_rectangle(hx - 4, hy - 4, hx + 4, hy + 4, fill="white",
                                   outline=color, width=2, tags="box")

    # ---- 마우스: 움직임
    def on_motion(self, event):
        c = self.canvas
        c.delete("cross")
        if self.pyramid and self.overlay.on_motion(event.x, event.y):
            return                      # Zoom 막대 / 미니맵 위
        if self.mode in ("draw", "pan"):
            c.configure(cursor=MODE_CURSORS[self.mode])

        if self.mode == "draw":
            c.create_line(event.x, 0, event.x, c.winfo_height(), fill="#64D2FF",
                          dash=(2, 4), tags="cross")
            c.create_line(0, event.y, c.winfo_width(), event.y, fill="#64D2FF",
                          dash=(2, 4), tags="cross")
            c.tag_raise("overlay")
        elif self.mode == "select" and self.s.cur:
            handle = self.hit_handle(event.x, event.y)
            if handle:
                c.configure(cursor=HANDLE_CURSORS[handle])
            else:
                ix, iy = self.view.to_image(event.x, event.y)
                on_box = self.s.find_box_at(ix, iy) is not None
                c.configure(cursor="fleur" if on_box else "arrow")

        if self.s.cur:
            ix, iy = self.view.to_image(event.x, event.y)
            self.zoom_var.set(f"원본 ({ix:.0f}, {iy:.0f})   배율 {self.view.scale * 100:.0f}%")

    # ---- 마우스: 왼쪽 버튼 누름
    def on_left_down(self, event):
        # 메뉴가 열려 있을 때의 클릭은 메뉴를 닫는 용도로만 쓴다.
        if self.menubar.is_open():
            self.menubar.close()
            return
        if not self.s.cur:
            return

        self.canvas.focus_set()
        part = self.overlay.hit(event.x, event.y)       # Zoom 막대 / 미니맵을 눌렀으면 그것만 처리
        if part == "hud":
            self.overlay.click(event.x, event.y)
            return
        if part == "map":
            self.drag = dict(kind="map")
            self.overlay.map_jump(event.x, event.y)
            return
        if self.mode == "pan":
            self.on_pan_start(event)
            return

        ix, iy = self.view.to_image(event.x, event.y)

        # 핸들을 잡았으면 크기 조절 (새 BBox / 선택 이동 모드 공통)
        handle = self.hit_handle(event.x, event.y)
        if handle:
            box = self.s.cur.boxes[self.selected]
            self.drag = dict(kind="resize", h=handle, orig=box.normalized(),
                             pushed=False, sx=event.x, sy=event.y)
            return

        if self.mode == "select":
            hit = self.s.find_box_at(ix, iy)
            self.selected = hit
            if hit is not None:
                self.select_class_of(hit)
                self.drag = dict(kind="move", orig=self.s.cur.boxes[hit].normalized(),
                                 pushed=False, ix=ix, iy=iy, sx=event.x, sy=event.y)
            self.draw_boxes()
            return

        self.drag = dict(kind="draw", ix=ix, iy=iy, sx=event.x, sy=event.y)

    # ---- 마우스: 왼쪽 버튼 드래그
    def on_left_drag(self, event):
        if self.drag and self.drag["kind"] == "map":
            self.overlay.map_jump(event.x, event.y)
            return
        if self.mode == "pan" and self.pan_last:
            self.on_pan_drag(event)
            return

        d = self.drag
        if not d:
            return

        if d["kind"] == "draw":
            self.canvas.delete("rubber")
            color = CLASS_COLORS.get(self.class_var.get(), "#ffffff")
            self.canvas.create_rectangle(d["sx"], d["sy"], event.x, event.y, outline=color,
                                         width=2, dash=(4, 2), tags="rubber")
            return

        # 이동/크기 조절: 실제로 끌기 시작할 때 Undo 를 한 번만 쌓는다.
        if not d["pushed"]:
            if abs(event.x - d["sx"]) < DRAG_START_PX and abs(event.y - d["sy"]) < DRAG_START_PX:
                return
            self.s.begin_edit()
            d["pushed"] = True

        cur = self.s.cur
        o = d["orig"]
        ix, iy = self.view.to_image(event.x, event.y)

        if d["kind"] == "move":
            # 크기는 그대로, 이미지 밖으로는 못 나가게
            dx = max(-o.x1, min(cur.width - o.x2, ix - d["ix"]))
            dy = max(-o.y1, min(cur.height - o.y2, iy - d["iy"]))
            new_box = Box(o.cls, o.x1 + dx, o.y1 + dy, o.x2 + dx, o.y2 + dy)
        else:
            # 핸들 이름(n, s, e, w 조합)에 들어 있는 방향의 변만 움직인다.
            x1, y1, x2, y2 = o.x1, o.y1, o.x2, o.y2
            if "w" in d["h"]:
                x1 = ix
            if "e" in d["h"]:
                x2 = ix
            if "n" in d["h"]:
                y1 = iy
            if "s" in d["h"]:
                y2 = iy
            new_box = Box(o.cls, x1, y1, x2, y2)

        self.s.replace_box(self.selected, new_box, push_undo=False)
        self.draw_boxes()

    # ---- 마우스: 왼쪽 버튼 놓음
    def on_left_up(self, event):
        self.canvas.delete("rubber")
        d, self.drag = self.drag, None
        if self.mode == "pan":
            self.pan_last = None
            return
        if not d or d["kind"] == "map":
            return

        if d["kind"] in ("move", "resize"):
            if d["pushed"]:
                cur = self.s.cur
                cur.boxes[self.selected] = cur.boxes[self.selected].normalized()
                self.after_edit()
            return

        # 새 BBox 모드에서 거의 안 움직였으면 클릭 = BBox 선택
        if abs(event.x - d["sx"]) < CLICK_PX or abs(event.y - d["sy"]) < CLICK_PX:
            self.selected = self.s.find_box_at(d["ix"], d["iy"])
            if self.selected is not None:
                self.select_class_of(self.selected)
            self.draw_boxes()
            return

        cls = self.class_var.get()
        if cls not in ACTIVE_CLASS_IDS:
            messagebox.showwarning("Class", "Class 4 는 새 BBox 에 사용할 수 없습니다.")
            return

        x2, y2 = self.view.to_image(event.x, event.y)
        box = self.s.add_box(cls, d["ix"], d["iy"], x2, y2)
        if box is None:
            self.status_bar.set("BBox 가 너무 작아 만들지 않았습니다.")
            return

        self.selected = len(self.s.cur.boxes) - 1
        self.after_edit()

    # ---- 화면 이동 (Pan)
    def on_pan_start(self, event):
        self.pan_last = (event.x, event.y)

    def on_pan_drag(self, event):
        if self.pan_last is None:
            return
        last_x, last_y = self.pan_last
        self.view.pan(event.x - last_x, event.y - last_y)
        self.pan_last = (event.x, event.y)
        self.fit_mode = False
        self.render()

    def on_pan_end(self, _event):
        self.pan_last = None
