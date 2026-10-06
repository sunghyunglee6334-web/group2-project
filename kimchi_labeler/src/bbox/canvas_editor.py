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
from ..ui.style import HANDLE_CURSORS, HANDLE_RADIUS
from ..yolo.yolo_io import Box

DRAG_START_PX = 3       # 이보다 적게 움직이면 클릭으로 본다
CLICK_PX = 4            # 새 BBox 모드에서 이보다 짧게 끌면 'BBox 선택' 클릭


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
        self.view.fit(width, height, self.canvas.winfo_width(), self.canvas.winfo_height())
        self.fit_mode = True
        self.render()

    def zoom_at(self, factor, x, y):
        if not self.pyramid:
            return
        self.view.zoom_at(factor, x, y)
        self.fit_mode = False
        self.render()

    def zoom_center(self, factor):
        self.zoom_at(factor, self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)

    def on_wheel(self, event):
        self.zoom_at(1.25 if event.delta > 0 else 0.8, event.x, event.y)

    def on_resize(self, _event):
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
            c.create_text(10, 10, text="라벨 숨김 (H 로 다시 보기)", anchor="nw",
                          fill="#fbbf24", font=("", 10, "bold"), tags="box")
        else:
            for i, box in enumerate(cur.boxes):
                self._draw_one_box(i, box)

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

        # Class 이름표: 위에 공간이 없으면 BBox 안쪽에 붙인다.
        label = f"{box.cls} {CLASS_NAMES.get(box.cls, '?')}"
        ty = y1 - 19 if y1 > 21 else y1 + 2
        text_id = c.create_text(x1 + 5, ty + 2, text=label, anchor="nw", fill="white",
                                font=("", 10, "bold"), tags="box")
        right = c.bbox(text_id)[2]
        bg_id = c.create_rectangle(x1, ty, right + 5, ty + 19, fill=color, outline="", tags="box")
        c.tag_lower(bg_id, text_id)

        if selected:
            for hx, hy in self.handles(box).values():
                c.create_rectangle(hx - 4, hy - 4, hx + 4, hy + 4, fill="white",
                                   outline=color, width=2, tags="box")

    # ---- 마우스: 움직임
    def on_motion(self, event):
        c = self.canvas
        c.delete("cross")

        if self.mode == "draw":
            c.create_line(event.x, 0, event.x, c.winfo_height(), fill="#22d3ee",
                          dash=(2, 4), tags="cross")
            c.create_line(0, event.y, c.winfo_width(), event.y, fill="#22d3ee",
                          dash=(2, 4), tags="cross")
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
        if self.mode == "pan":
            self.pan_last = None
            return

        d, self.drag = self.drag, None
        if not d:
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
