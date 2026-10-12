"""토스 스타일 부품: 둥근 카드, 둥근 버튼, 탭, 카드형 목록, 막대 그래프, 알약 라벨, 스크롤 패널.

Tkinter 기본 위젯은 각지고 OS 마다 모양이 달라서, 대부분 Canvas 에 직접 그려서 만든다.
"""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from .icons import arrow_badge, icon_image
from .style import (BG, BLUE, BLUE_HOVER, BLUE_PRESS, BLUE_SOFT, BLUE_SOFT_HOVER, CARD, FILL,
                    FILL_HOVER, FILL_PRESS, FONT, FONT_BOLD, FONT_BUTTON, FONT_CAPTION, FONT_SMALL,
                    FONT_SMALL_BOLD, LINE, RED, TEXT, TEXT2, TEXT3, TEXT4, text_on)


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """둥근 사각형 (polygon + smooth)."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def parent_bg(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return BG


# ==================================================================== 둥근 카드
class Card(tk.Frame):
    """둥근 모서리 카드. 내용은 card.body (Frame) 에 넣는다.

    바깥 Frame 뒤에 Canvas 를 깔아 둥근 사각형을 그리고, 그 위에 body 를 여백만큼 안쪽에 둔다.
    크기는 보통 Frame 처럼 내용에 맞춰 정해진다 (expand=True 면 body 가 카드 크기만큼 늘어남).
    """

    def __init__(self, parent, fill=CARD, radius=20, padx=20, pady=18, expand=False, **kw):
        super().__init__(parent, bg=parent_bg(parent), bd=0, highlightthickness=0, **kw)
        self.fill, self.radius = fill, radius
        self.bg_canvas = tk.Canvas(self, bg=parent_bg(parent), highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=fill)
        self.body.pack(fill=tk.BOTH, expand=expand, padx=padx, pady=pady)
        self.tk.call("lower", self.bg_canvas._w)      # 캔버스를 body 뒤로 (Canvas.lower 는 도형용이라 직접 호출)
        self.bind("<Configure>", self._redraw, add="+")

    def _redraw(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        c = self.bg_canvas
        c.delete("all")
        if w > 1 and h > 1:
            round_rect(c, 0, 0, w, h, self.radius, fill=self.fill, outline=self.fill)

    def set_fill(self, fill):
        self.fill = fill
        self.body.configure(bg=fill)
        self._redraw()


# ==================================================================== 둥근 버튼
VARIANTS = {
    #           바탕          hover            눌림           글자    테두리
    "primary": (BLUE, BLUE_HOVER, BLUE_PRESS, "white", None),
    "soft": (BLUE_SOFT, BLUE_SOFT_HOVER, "#C9E2FF", BLUE, None),
    "gray": (FILL, FILL_HOVER, FILL_PRESS, TEXT2, None),
    "white": (CARD, FILL, FILL_HOVER, TEXT2, LINE),
    "danger": (FILL, FILL_HOVER, FILL_PRESS, RED, None),
    "ghost": (None, FILL, FILL_HOVER, TEXT2, None),
}


class RoundButton(tk.Canvas):
    """둥근 버튼. variant: primary / soft / gray / white / danger / ghost

    set_active(True) 면 '선택됨' 모양 (연한 파랑 + 파란 글자, outline_active=True 면 파란 테두리).
    """

    def __init__(self, parent, text, command=None, variant="gray", height=40, width=None,
                 font=FONT_BUTTON, padx=16, radius=12, tooltip=None, outline_active=False,
                 arrow=0):
        """arrow=지름(px) 을 주면 글자 오른쪽에 동그란 화살표를 붙인다 ('저장하고 다음')."""
        self.bg_parent = parent_bg(parent)
        super().__init__(parent, height=height, bg=self.bg_parent, highlightthickness=0, bd=0,
                         takefocus=0, cursor="hand2")
        self.text, self.command, self.variant = text, command, variant
        self.font, self.padx, self.radius = font, padx, radius
        self.fixed_width = width
        self.outline_active = outline_active
        self.active_style = None    # (바탕, 글자, 테두리) - 선택됐을 때 색을 버튼마다 다르게
        self.hover = self.pressed = self.active = False
        self.enabled = True
        self.fg_override = None
        self.arrow = arrow
        self.arrow_gap = 10

        self._resize_to_text()
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        if tooltip:
            Tooltip(self, tooltip)

    def _resize_to_text(self):
        if self.fixed_width:
            self.configure(width=self.fixed_width)
            return
        tmp = self.create_text(0, 0, text=self.text, font=self.font)
        x1, _, x2, _ = self.bbox(tmp)
        self.delete(tmp)
        extra = self.arrow + self.arrow_gap if self.arrow else 0
        self.configure(width=(x2 - x1) + extra + self.padx * 2)

    def set_text(self, text, fg=None):
        self.text = text
        self.fg_override = fg
        self._resize_to_text()
        self.redraw()

    def set_active(self, on):
        if on != self.active:
            self.active = on
            self.redraw()

    def set_variant(self, variant):
        self.variant = variant
        self.redraw()

    def set_enabled(self, on):
        self.enabled = on
        self.configure(cursor="hand2" if on else "arrow")
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w, h = int(float(self.cget("width"))), int(float(self.cget("height")))
        base, hover, press, fg, outline = VARIANTS[self.variant]
        if self.active:
            base, hover, press, fg = BLUE_SOFT, BLUE_SOFT_HOVER, "#C9E2FF", BLUE
            outline = BLUE if self.outline_active else None
            if self.active_style:
                base, fg, line = self.active_style
                hover = press = base
                outline = line if self.outline_active else None
        fill = press if self.pressed else hover if self.hover else base
        if not self.enabled:
            fg = TEXT4
        if self.fg_override and not self.active:
            fg = self.fg_override
        if fill or outline:
            width = 2 if (self.active and outline) else 1
            inset = width / 2
            round_rect(self, inset, inset, w - inset, h - inset, self.radius,
                       fill=fill or self.bg_parent, outline=outline or fill or self.bg_parent, width=width)
        if not self.arrow:
            self.create_text(w / 2, h / 2, text=self.text, fill=fg, font=self.font)
            return
        # 글자 + 화살표를 한 덩어리로 보고 가운데 정렬
        tid = self.create_text(0, h / 2, text=self.text, fill=fg, font=self.font, anchor="w")
        x1, _, x2, _ = self.bbox(tid)
        left = w / 2 - ((x2 - x1) + self.arrow_gap + self.arrow) / 2
        self.move(tid, left - x1, 0)
        self.create_image(left + (x2 - x1) + self.arrow_gap, h / 2 + 1, anchor="w",
                          image=arrow_badge(self, self.arrow))

    def _enter(self, _e):
        self.hover = True
        self.redraw()

    def _leave(self, _e):
        self.hover = self.pressed = False
        self.redraw()

    def _press(self, _e):
        if self.enabled:
            self.pressed = True
            self.redraw()

    def _release(self, e):
        was, self.pressed = self.pressed, False
        self.redraw()
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        if was and inside and self.enabled and self.command:
            self.command()


class ChoiceGroup(tk.Frame):
    """같은 크기의 버튼 여러 개 중 하나만 선택 (검수 상태 PASS / 수정 / 확인 필요 / 검수 완료)."""

    def __init__(self, parent, options, variable, command=None, height=40, gap=6, styles=None):
        """styles = {값: (바탕, 글자, 테두리)} 를 주면 선택된 버튼을 그 색으로 칠한다."""
        super().__init__(parent, bg=parent_bg(parent))
        self.var = variable
        self.buttons = {}
        for i, (value, label) in enumerate(options):
            self.columnconfigure(i, weight=1, uniform="choice")
            b = RoundButton(self, label, lambda v=value: self._pick(v, command), variant="gray",
                            height=height, padx=4, font=FONT_SMALL_BOLD, outline_active=True)
            b.active_style = (styles or {}).get(value)
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else gap, 0))
            self.buttons[value] = b
        variable.trace_add("write", lambda *a: self.refresh())
        self.refresh()

    def _pick(self, value, command):
        self.var.set(value)
        if command:
            command(value)

    def refresh(self):
        current = self.var.get()
        for value, b in self.buttons.items():
            b.set_active(value == current)


# ==================================================================== 밑줄 탭
class Tabs(tk.Canvas):
    """토스 탭 (선택된 탭 아래에 검은 밑줄). options = [(값, 글자), ...]"""

    def __init__(self, parent, options, variable, command=None, height=46):
        super().__init__(parent, height=height, bg=parent_bg(parent), highlightthickness=0, bd=0,
                         cursor="hand2")
        self.options, self.var, self.command = options, variable, command
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonRelease-1>", self._click)
        variable.trace_add("write", lambda *a: self.redraw())

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        n = len(self.options)
        seg = w / n
        self.create_line(0, h - 1, w, h - 1, fill=FILL)
        for i, (value, label) in enumerate(self.options):
            on = value == self.var.get()
            cx = seg * i + seg / 2
            tid = self.create_text(cx, h / 2 - 1, text=label, font=FONT_BOLD, fill=TEXT if on else TEXT3)
            if on:
                x1, _, x2, _ = self.bbox(tid)
                self.create_rectangle(x1 - 10, h - 3, x2 + 10, h - 1, fill=TEXT, outline=TEXT)

    def _click(self, e):
        n = len(self.options)
        i = min(n - 1, max(0, int(e.x / (self.winfo_width() / n))))
        value = self.options[i][0]
        if self.command:
            self.command(value)
        else:
            self.var.set(value)


# ==================================================================== 카드형 목록
class RichList(tk.Canvas):
    """토스 거래내역 같은 목록 (동그란 아이콘 + 두 줄 글자 + 오른쪽 상태).

    rows = [dict(icon='1', icon_bg=색, title='파일명', sub='설명', right='PASS', right_fg=색, dim=False)]
    보이는 줄만 그리므로 900줄이어도 빠르다.
    """

    def __init__(self, parent, on_select, row_h=56, icon_d=34, two_line=True, pad=10, scroll=True,
                 title_font=FONT_BOLD, right_font=FONT_SMALL_BOLD):
        super().__init__(parent, bg=parent_bg(parent), highlightthickness=0, bd=0, takefocus=0)
        self.on_select = on_select
        self.row_h, self.icon_d, self.two_line, self.pad, self.scroll = row_h, icon_d, two_line, pad, scroll
        self.title_font, self.right_font = title_font, right_font
        self._fonts = {}
        self.rows = []
        self.selected = None
        self.hover = None
        self.top = 0                    # 스크롤 위치 (px)
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<ButtonRelease-1>", self._click)
        self._drag = None               # 스크롤바를 잡고 끄는 중이면 (시작 y, 시작 top)
        self._sb_hot = False            # 마우스가 스크롤바 위에 있는지
        if scroll:
            self.bind("<MouseWheel>", lambda e: self.scroll_by(-3 if e.delta > 0 else 3))
            self.bind("<Button-4>", lambda e: self.scroll_by(-3))
            self.bind("<Button-5>", lambda e: self.scroll_by(3))
            self.bind("<ButtonPress-1>", self._press)
            self.bind("<B1-Motion>", self._drag_move)

    # ---- 데이터
    def set_rows(self, rows):
        self.rows = rows
        self.top = min(self.top, self._max_top())
        if not self.scroll:
            self.configure(height=len(rows) * self.row_h + 8)
        self.redraw()

    def update_row(self, i, row):
        if 0 <= i < len(self.rows):
            self.rows[i] = row
            self.redraw()

    def set_selected(self, i, see=True):
        self.selected = i
        if see and i is not None:
            self.see(i)
        self.redraw()

    # ---- 스크롤
    def _max_top(self):
        return max(0, len(self.rows) * self.row_h + 8 - self.winfo_height())

    def scroll_by(self, rows):
        self.top = max(0, min(self._max_top(), self.top + rows * self.row_h))
        self.redraw()

    def see(self, i):
        h = self.winfo_height()
        if h <= 1:
            return
        y1, y2 = 4 + i * self.row_h, 4 + (i + 1) * self.row_h
        if y1 < self.top:
            self.top = y1 - 4
        elif y2 > self.top + h:
            self.top = y2 - h + 4
        self.top = max(0, min(self._max_top(), self.top))

    # ---- 그리기
    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or not self.rows:
            return
        first = max(0, int((self.top - 4) // self.row_h))
        last = min(len(self.rows), int((self.top + h) // self.row_h) + 1)
        for i in range(first, last):
            self._draw_row(i, self.rows[i], 4 + i * self.row_h - self.top, w)

        thumb = self._thumb()
        if thumb:                               # 스크롤바 (잡고 끌 수 있음)
            ty, th = thumb
            hot = self._sb_hot or self._drag
            x1 = w - (10 if hot else 7)
            color = TEXT3 if hot else TEXT4
            round_rect(self, x1, ty + 2, w - 2, ty + th - 2, 4, fill=color, outline=color)

    # ---- 스크롤바 잡고 끌기
    SB_HIT = 14                                 # 오른쪽 끝에서 이만큼은 스크롤바 영역

    def _thumb(self):
        """(위치 y, 높이). 스크롤할 필요 없으면 None"""
        h = self.winfo_height()
        total = len(self.rows) * self.row_h + 8
        if not self.scroll or total <= h or h <= 1:
            return None
        th = max(30, h * h / total)
        ty = (h - th) * (self.top / max(1, total - h))
        return ty, th

    def _on_bar(self, e):
        return self._thumb() is not None and e.x >= self.winfo_width() - self.SB_HIT

    def _press(self, e):
        self._drag = None
        if not self._on_bar(e):
            return
        ty, th = self._thumb()
        if not (ty <= e.y <= ty + th):          # 빈 곳을 누르면 그 위치로 바로 이동
            h = self.winfo_height()
            ratio = (e.y - th / 2) / max(1, h - th)
            self.top = max(0, min(self._max_top(), ratio * self._max_top()))
            self.redraw()
        self._drag = (e.y, self.top)

    def _drag_move(self, e):
        if not self._drag:
            return
        ty, th = self._thumb() or (0, 0)
        h = self.winfo_height()
        y0, top0 = self._drag
        per_px = self._max_top() / max(1, h - th)
        self.top = max(0, min(self._max_top(), top0 + (e.y - y0) * per_px))
        self.redraw()

    def _draw_row(self, i, row, y, w):
        p = self.pad
        if i == self.selected:
            round_rect(self, p, y + 2, w - p, y + self.row_h - 2, 14, fill=BLUE_SOFT, outline=BLUE_SOFT)
        elif i == self.hover:
            round_rect(self, p, y + 2, w - p, y + self.row_h - 2, 14, fill=FILL, outline=FILL)

        d = self.icon_d
        cx, cy = p + 12 + d / 2, y + self.row_h / 2
        icon_bg = row.get("icon_bg", TEXT4)
        icon = row.get("icon", "")
        fg = row.get("icon_fg") or text_on(icon_bg)
        # 원과 기호는 Pillow 로 부드럽게 그린 이미지 (Canvas 원은 테두리가 깨져 보임)
        kind = {"@check": "check", "@check2": "check2", "@edit": "edit", "!": "alert"}.get(icon, "")
        self.create_image(cx, cy, image=icon_image(self, kind, icon_bg, fg, int(d)))
        if icon and not kind:            # 숫자 같은 글자는 위에 글자로
            self.create_text(cx, cy, text=icon, fill=fg, font=FONT_SMALL_BOLD)

        tx = cx + d / 2 + 12
        dim = row.get("dim")
        # 오른쪽 상태 글자를 먼저 그리고, 남는 폭에 맞춰 제목을 '…' 로 줄인다 (글자 겹침 방지)
        right_x = w - p - 14
        title_max = right_x - tx - 10
        if row.get("right"):
            rid = self.create_text(right_x, cy, text=row["right"], anchor="e", font=self.right_font,
                                   fill=row.get("right_fg", TEXT3))
            title_max = self.bbox(rid)[0] - tx - 10
        title = self._fit(row.get("title", ""), self.title_font, title_max)
        if self.two_line:
            self.create_text(tx, cy - 9, text=title, anchor="w", font=self.title_font,
                             fill=TEXT4 if dim else TEXT)
            self.create_text(tx, cy + 10, text=self._fit(row.get("sub", ""), FONT_CAPTION, title_max),
                             anchor="w", font=FONT_CAPTION, fill=TEXT3)
        else:
            self.create_text(tx, cy, text=title, anchor="w", font=self.title_font,
                             fill=TEXT4 if dim else TEXT)

    def _fit(self, text, font, max_w):
        """글자가 max_w 보다 길면 뒤를 잘라 '…' 를 붙인다 (확장자는 남겨서 파일 구분이 되게)."""
        f = self._fonts.get(font)
        if f is None:
            f = self._fonts[font] = tkfont.Font(root=self, font=font)
        if max_w <= 0 or f.measure(text) <= max_w:
            return text
        head, dot, ext = text.rpartition(".")
        tail = "…" + (dot + ext if head and len(ext) <= 4 else "")
        body = head if head and len(ext) <= 4 else text
        while body and f.measure(body + tail) > max_w:
            body = body[:-1]
        return body + tail

    # ---- 마우스
    def _index_at(self, y):
        i = int((y + self.top - 4) // self.row_h)
        return i if 0 <= i < len(self.rows) else None

    def _set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self.redraw()

    def _motion(self, e):
        hot = self._on_bar(e)
        if hot != self._sb_hot:
            self._sb_hot = hot
            self.redraw()
        self._set_hover(None if hot else self._index_at(e.y))

    def _click(self, e):
        if self._drag is not None or self._on_bar(e):   # 스크롤바 조작은 선택이 아님
            self._drag = None
            self.redraw()
            return
        i = self._index_at(e.y)
        if i is not None:
            self.on_select(i)


# ==================================================================== 막대 그래프
class BarChart(tk.Canvas):
    """'작업 현황' 카드의 상태별 가로 막대. rows = [(이름, 개수, 색)], total = 전체 장수"""

    ROW_H = 24

    def __init__(self, parent):
        super().__init__(parent, bg=parent_bg(parent), highlightthickness=0, bd=0, height=10)
        self.rows, self.total = [], 1
        self.bind("<Configure>", lambda e: self.redraw())

    def set(self, rows, total):
        self.rows, self.total = rows, max(1, total)
        self.configure(height=len(rows) * self.ROW_H)
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        if w <= 1:
            return
        x1, x2 = 74, w - 40
        for i, (name, n, color) in enumerate(self.rows):
            cy = i * self.ROW_H + self.ROW_H / 2
            self.create_text(0, cy, text=name, anchor="w", font=FONT_CAPTION, fill=TEXT3)
            round_rect(self, x1, cy - 4, x2, cy + 4, 4, fill=FILL, outline=FILL)
            if n:
                xe = x1 + max(8, (x2 - x1) * n / self.total)
                round_rect(self, x1, cy - 4, xe, cy + 4, 4, fill=color, outline=color)
            self.create_text(w, cy, text=str(n), anchor="e", font=FONT_SMALL_BOLD, fill=TEXT2)


# ==================================================================== 알약 라벨
class Pill(tk.Canvas):
    """'● 저장 안 됨' 같은 작은 둥근 라벨. set('') 이면 숨김."""

    def __init__(self, parent, height=28, font=FONT_SMALL_BOLD):
        super().__init__(parent, height=height, width=1, bg=parent_bg(parent), highlightthickness=0, bd=0)
        self.font = font

    def set(self, text, fg=TEXT2, bg=FILL):
        self.delete("all")
        if not text:
            self.configure(width=1)
            return
        h = int(float(self.cget("height")))
        tid = self.create_text(0, h / 2, text=text, anchor="w", font=self.font, fill=fg)
        x1, _, x2, _ = self.bbox(tid)
        w = (x2 - x1) + 24
        self.configure(width=w)
        self.coords(tid, 12, h / 2)
        bgid = round_rect(self, 0, 0, w, h, h / 2, fill=bg, outline=bg)
        self.tag_lower(bgid)


# ==================================================================== 스크롤 패널
class ScrollFrame(tk.Frame):
    """세로로 스크롤되는 패널. 내용은 self.body 에 넣는다."""

    def __init__(self, parent, bg=BG, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.body = tk.Frame(self.canvas, bg=bg)
        self.window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window, width=e.width))
        self.bind("<Enter>", lambda e: self._bind_wheel(True), add="+")
        self.bind("<Leave>", lambda e: self._bind_wheel(False), add="+")

    def _on_scroll(self, first, last):
        if float(first) <= 0 and float(last) >= 1:
            self.bar.pack_forget()
        elif not self.bar.winfo_ismapped():
            self.bar.pack(side=tk.RIGHT, fill=tk.Y, before=self.canvas)
        self.bar.set(first, last)

    def _bind_wheel(self, on):
        for s in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            if on:
                self.bind_all(s, self._wheel)
            else:
                self.unbind_all(s)

    def _wheel(self, e):
        if isinstance(e.widget, tk.Text):
            return
        if not str(e.widget).startswith(str(self)):
            return
        if getattr(e, "num", None) == 4 or getattr(e, "delta", 0) > 0:
            self.canvas.yview_scroll(-2, "units")
        else:
            self.canvas.yview_scroll(2, "units")


# ==================================================================== 입력칸
def flat_entry(parent, textvariable=None, font=FONT, width=8, justify=tk.LEFT):
    """회색 타일 안에 넣는 테두리 없는 입력칸."""
    bg = parent_bg(parent)
    return tk.Entry(parent, textvariable=textvariable, width=width, relief=tk.FLAT, bd=0, font=font,
                    bg=bg, fg=TEXT, insertbackground=BLUE, justify=justify, highlightthickness=0,
                    disabledbackground=bg, readonlybackground=bg, selectbackground="#C9E2FF",
                    selectforeground=TEXT)


def tile(parent, label, var=None, font=FONT_BOLD, entry=True):
    """회색 둥근 칸: 위에 작은 회색 이름, 아래에 값 (entry=True 면 입력 가능).  반환 (card, 값 위젯)"""
    card = Card(parent, fill=FILL, radius=12, padx=12, pady=8)
    tk.Label(card.body, text=label, bg=FILL, fg=TEXT3, font=FONT_CAPTION, anchor="w").pack(fill=tk.X)
    if entry:
        w = flat_entry(card.body, var, font=font)
    else:
        w = tk.Label(card.body, textvariable=var, bg=FILL, fg=TEXT, font=font, anchor="w")
    w.pack(fill=tk.X, pady=(1, 0))
    return card, w


# ==================================================================== 툴팁
class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip, self.job = widget, text, None, None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e):
        self.job = self.widget.after(600, self._show)

    def _show(self):
        self.job = None
        root = self.widget.winfo_toplevel()
        x = self.widget.winfo_rootx() - root.winfo_rootx()
        y = self.widget.winfo_rooty() - root.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Label(root, text=self.text, bg="#333D4B", fg="white", font=FONT_SMALL,
                            padx=10, pady=5)
        self.tip.update_idletasks()
        x = max(4, min(x, root.winfo_width() - self.tip.winfo_reqwidth() - 8))
        self.tip.place(x=x, y=y)
        self.tip.lift()

    def _hide(self, _e=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None
