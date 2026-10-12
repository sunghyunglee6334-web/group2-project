"""메뉴 막대 (파일 · 보기 · 도구 · 검수 · 통계 · 도움말).

tk.Menu 대신 직접 만든다. WSLg 에서 tk.Menu 의 드롭다운(별도 override-redirect 창)이
닫힌 뒤에도 화면에 잔상으로 남기 때문이다. 드롭다운을 메인 창 안의 Frame 으로 띄우면
메인 창이 직접 다시 그리므로 이 문제가 없다.

    bar = MenuBar(root)
    bar.add_menu("파일(F)", [command("저장", save, "Ctrl+S"), SEPARATOR, ...], underline=3)
    bar.pack(side=tk.TOP, fill=tk.X)
"""
import tkinter as tk

from .style import BG, BLUE_SOFT, FONT, FONT_SMALL, LINE, TEXT, TEXT3

SUB_TEXT = TEXT3

CLICK_GUARD = "MenuClickGuard"     # 메뉴가 열려 있을 때 바깥 클릭을 막는 bindtag

BAR_BG = BG
POPUP_BG = "#ffffff"
HOVER_BG = BLUE_SOFT
BORDER = LINE

SEPARATOR = {"kind": "separator"}


def command(label, func, accel=""):
    return {"kind": "command", "label": label, "func": func, "accel": accel}


def radio(label, variable, value, func=None):
    return {"kind": "radio", "label": label, "variable": variable, "value": value, "func": func}


def submenu(label, items):
    return {"kind": "submenu", "label": label, "items": items}


class MenuBar(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BAR_BG, bd=0, highlightthickness=0)
        self.root = master.winfo_toplevel()
        self.menus = []             # [(제목 Label, 항목 목록)]
        self.current = None         # 지금 열린 메뉴 번호
        self.dropdown = None        # 지금 열린 드롭다운
        self.key_target = None      # 방향키가 움직일 드롭다운 (본 메뉴 또는 하위 메뉴)
        self.focus_before = None
        self.opened_by_hover = False
        self.anchors = {}           # 메뉴 번호 -> (드롭다운을 붙일 위젯, 'left' | 'right')

        # 메뉴가 열려 있는 동안 키보드는 메뉴 막대가 받는다.
        # 창(root)의 단축키(A, D, Space ...)가 같이 눌리지 않도록 root 태그는 뺀다.
        self.bindtags((str(self), "all"))
        self.bind("<Down>", lambda e: self._key_move(1))
        self.bind("<Up>", lambda e: self._key_move(-1))
        self.bind("<Right>", lambda e: self._key_right())
        self.bind("<Left>", lambda e: self._key_left())
        self.bind("<Return>", lambda e: self._key_enter())
        self.bind("<space>", lambda e: self._key_enter())
        self.bind("<Escape>", lambda e: self._key_escape())

        self.root.bind_all("<ButtonPress>", self._on_any_press, add="+")
        self.bind_class(CLICK_GUARD, "<ButtonPress>", self._on_guarded_press)
        self.root.bind("<Configure>", self._on_root_configure, add="+")
        self.root.bind("<Unmap>", self._on_root_unmap, add="+")
        self.root.bind("<FocusOut>", self._on_focus_out, add="+")
        self.root.bind("<F10>", lambda e: self._open_by_key(0), add="+")

    # ---- 메뉴 추가
    def add_menu(self, text, items, underline=-1, anchor=None, align="left"):
        """anchor 위젯을 주면 막대에 제목을 그리지 않고, 그 위젯 아래에 드롭다운을 연다.
        (토스 디자인: 화면 위쪽 '조각김치 라벨링 ⌄' 와 '⋯' 버튼이 메뉴를 연다)"""
        index = len(self.menus)
        title = tk.Label(self, text=text, bg=BAR_BG, fg=TEXT, font=FONT_SMALL,
                         padx=10, pady=4, underline=underline)
        self.anchors[index] = (anchor, align)
        if anchor is None:
            title.pack(side=tk.LEFT)

        title.bind("<ButtonPress-1>", lambda e: self.toggle(index))
        title.bind("<B1-Motion>", self._on_title_drag)
        title.bind("<ButtonRelease-1>", self._on_release)
        title.bind("<Enter>", lambda e: self._on_title_enter(index))

        if 0 <= underline < len(text):
            key = text[underline].lower()
            self.root.bind(f"<Alt-{key}>", lambda e: self._open_by_key(index), add="+")
            self.root.bind(f"<Alt-{key.upper()}>", lambda e: self._open_by_key(index), add="+")

        self.menus.append((title, items))

    # ---- 열기 / 닫기
    def is_open(self):
        return self.current is not None

    def toggle(self, index):
        # hover 로 막 열린 메뉴는 클릭해도 닫지 않는다.
        if self.current == index and not self.opened_by_hover:
            self.close()
        else:
            self.open(index)
        self.opened_by_hover = False

    def open(self, index, select_first=False):
        if self.current is None:
            self.focus_before = self._focused_widget()
            self._set_click_guard(True)

        self._remove_dropdown()
        self.current = index
        self._paint_titles()

        title, items = self.menus[index]
        anchor, align = self.anchors.get(index, (None, "left"))
        if anchor is not None:
            x = anchor.winfo_rootx() + (anchor.winfo_width() if align == "right" else 0)
            y = anchor.winfo_rooty() + anchor.winfo_height() + 6
        else:
            x = title.winfo_rootx()
            y = title.winfo_rooty() + title.winfo_height()
        self.dropdown = Dropdown(self, items, x, y, align=align)
        self.key_target = self.dropdown

        self.focus_set()
        if select_first:
            self.dropdown.move(1)

    def close(self):
        if self.current is None:
            return
        self._remove_dropdown()
        self._set_click_guard(False)
        self.current = None
        self.key_target = None
        self.opened_by_hover = False
        self._paint_titles()

        widget, self.focus_before = self.focus_before, None
        try:
            if widget is not None and widget.winfo_exists():
                widget.focus_set()
            else:
                self.root.focus_set()
        except tk.TclError:
            pass

    def _remove_dropdown(self):
        if self.dropdown is not None:
            self.dropdown.vanish()
            self.dropdown = None

    def _open_by_key(self, index):
        if index < len(self.menus):
            self.open(index, select_first=True)
        return "break"

    # ---- 마우스
    def _on_title_enter(self, index):
        # 다른 메뉴가 열려 있으면 그 메뉴는 닫고 마우스가 올라간 메뉴를 연다.
        if self.current is not None and self.current != index:
            self.open(index)
            self.opened_by_hover = True

    def _on_title_drag(self, event):
        # 제목을 누른 채 끌고 다닐 때 (누른 위젯이 마우스 이벤트를 계속 받는다)
        widget = self.winfo_containing(event.x_root, event.y_root)
        for index, (title, _) in enumerate(self.menus):
            if widget is title and index != self.current:
                self.open(index)
                return

        found = self._row_at(event.x_root, event.y_root)
        if found:
            dropdown, pos = found
            dropdown.highlight(pos)

    def _on_release(self, event):
        found = self._row_at(event.x_root, event.y_root)
        if found:
            dropdown, pos = found
            dropdown.activate(pos)

    def _row_at(self, x, y):
        dropdown = self.dropdown
        while dropdown is not None:
            pos = dropdown.row_at(x, y)
            if pos is not None:
                return dropdown, pos
            dropdown = dropdown.child
        return None

    def _set_click_guard(self, on):
        """메뉴가 열려 있는 동안, 메뉴 바깥의 첫 클릭은 '메뉴 닫기'로만 쓴다.

        이게 없으면 메뉴를 닫으려고 이미지 목록을 눌렀는데 이미지가 바뀌거나,
        버튼을 눌렀는데 버튼이 실행되는 일이 생긴다.
        모든 위젯의 bindtags 맨 앞에 CLICK_GUARD 를 붙였다가, 닫을 때 뗀다.
        """
        for widget in self._all_widgets(self.root):
            if widget is self or str(widget).startswith(str(self) + "."):
                continue
            if any(isinstance(w, Dropdown) for w in self._ancestors(widget)):
                continue
            tags = widget.bindtags()
            if on and CLICK_GUARD not in tags:
                widget.bindtags((CLICK_GUARD,) + tags)
            elif not on and CLICK_GUARD in tags:
                widget.bindtags(tuple(t for t in tags if t != CLICK_GUARD))

    def _all_widgets(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self._all_widgets(child)

    @staticmethod
    def _ancestors(widget):
        while widget is not None:
            yield widget
            widget = widget.master

    def _on_guarded_press(self, _event):
        self.close()
        return "break"

    def _on_any_press(self, event):
        """메뉴 바깥을 누르면 닫는다."""
        if self.current is None:
            return
        path = str(event.widget)
        inside = [str(self)]
        dropdown = self.dropdown
        while dropdown is not None:
            inside.append(str(dropdown))
            dropdown = dropdown.child
        if not any(path == p or path.startswith(p + ".") for p in inside):
            self.close()

    def _on_root_configure(self, event):
        if event.widget is self.root:
            self.close()

    def _on_root_unmap(self, event):
        if event.widget is self.root:
            self.close()

    def _on_focus_out(self, _event):
        if self.current is not None:
            self.after(80, self._close_if_inactive)

    def _close_if_inactive(self):
        # 다른 프로그램으로 넘어가면 메뉴를 닫는다.
        if self._focused_widget() is None:
            self.close()

    def _focused_widget(self):
        try:
            return self.root.focus_get()
        except (KeyError, tk.TclError):
            return None

    def _paint_titles(self):
        # 열린 메뉴만 칠한다. hover 색은 쓰지 않음 (WSLg 는 <Leave> 를 가끔 빠뜨린다).
        for index, (title, _) in enumerate(self.menus):
            title.configure(bg=HOVER_BG if index == self.current else BAR_BG)

    # ---- 키보드
    def _key_move(self, step):
        if self.key_target is not None:
            self.key_target.move(step)
        return "break"

    def _key_enter(self):
        target = self.key_target
        if target is not None and target.active is not None:
            target.activate(target.active, by_key=True)
        return "break"

    def _key_right(self):
        target = self.key_target
        if target is not None and target.active is not None and target.active_item()["kind"] == "submenu":
            target.open_child(target.active)
            self.key_target = target.child
            self.key_target.move(1)
        elif self.current is not None:
            self.open((self.current + 1) % len(self.menus), select_first=True)
        return "break"

    def _key_left(self):
        target = self.key_target
        if target is not None and target.parent is not None:
            target.parent.close_child()
            self.key_target = target.parent
        elif self.current is not None:
            self.open((self.current - 1) % len(self.menus), select_first=True)
        return "break"

    def _key_escape(self):
        target = self.key_target
        if target is not None and target.parent is not None:
            target.parent.close_child()
            self.key_target = target.parent
        else:
            self.close()
        return "break"


class Dropdown(tk.Frame):
    """드롭다운 하나. 메인 창 안에 place() 로 띄우는 Frame."""

    def __init__(self, bar, items, x, y, parent=None, align="left"):
        super().__init__(bar.root, bg=POPUP_BG, bd=0)
        self.align = align
        self.bar = bar
        self.parent = parent
        self.child = None
        self.child_pos = None
        self.rows = []          # [(행 Frame, 항목)]
        self.active = None

        box = tk.Frame(self, bg=POPUP_BG, highlightthickness=1,
                       highlightbackground="#D1D6DB", highlightcolor="#D1D6DB", pady=6, padx=4)
        box.pack(fill=tk.BOTH, expand=True)

        for item in items:
            if item["kind"] == "separator":
                tk.Frame(box, height=1, bg=BORDER).pack(fill=tk.X, padx=8, pady=3)
            else:
                self._add_row(box, item)

        self._place(x, y)

    def _add_row(self, box, item):
        row = tk.Frame(box, bg=POPUP_BG)
        row.pack(fill=tk.X)
        row.columnconfigure(1, weight=1, minsize=150)

        right = "▸" if item["kind"] == "submenu" else item.get("accel", "")
        mark = tk.Label(row, text=self._mark(item), width=2, bg=POPUP_BG, fg=TEXT, font=FONT)
        label = tk.Label(row, text=item["label"], anchor="w", bg=POPUP_BG, fg=TEXT,
                         font=FONT, padx=4, pady=7)
        accel = tk.Label(row, text=right, anchor="e", bg=POPUP_BG, fg=SUB_TEXT,
                         font=FONT, padx=12)

        mark.grid(row=0, column=0)
        label.grid(row=0, column=1, sticky="w")
        accel.grid(row=0, column=2, sticky="e")

        pos = len(self.rows)
        for widget in (row, mark, label, accel):
            widget.bind("<Enter>", lambda e, p=pos: self.highlight(p))
            widget.bind("<ButtonRelease-1>", self.bar._on_release)

        self.rows.append((row, item))

    @staticmethod
    def _mark(item):
        if item["kind"] == "radio" and item["variable"].get() == item["value"]:
            return "●"
        return ""

    def _place(self, x, y):
        """x, y 는 화면 좌표. 메인 창 안 좌표로 바꾸고, 창 밖으로 잘리지 않게 맞춘다."""
        root = self.bar.root
        self.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        if self.align == "right":
            x -= width
        x = x - root.winfo_rootx()
        y = y - root.winfo_rooty()
        if self.parent is not None and x + width > root.winfo_width():
            # 하위 메뉴가 오른쪽 창 밖으로 나가면 부모 메뉴의 왼쪽에 연다
            x = self.parent.winfo_rootx() - root.winfo_rootx() - width + 4
        x = max(0, min(x, root.winfo_width() - width))
        y = max(0, min(y, root.winfo_height() - height))
        self.place(x=x, y=y)
        self.lift()             # 다른 위젯보다 위에 보이게

    # ---- 항목 강조
    def highlight(self, pos, open_child=True):
        self.bar.key_target = self
        self.bar.opened_by_hover = False
        if pos == self.active:
            return

        if self.active is not None:
            self._paint(self.active, POPUP_BG)
        self.active = pos
        self._paint(pos, HOVER_BG)

        if self.rows[pos][1]["kind"] == "submenu":
            if open_child:
                self.open_child(pos)
        else:
            self.close_child()

    def _paint(self, pos, color):
        row = self.rows[pos][0]
        row.configure(bg=color)
        for widget in row.winfo_children():
            widget.configure(bg=color)

    def move(self, step):
        if not self.rows:
            return
        if self.active is None:
            pos = 0 if step > 0 else len(self.rows) - 1
        else:
            pos = (self.active + step) % len(self.rows)
        self.highlight(pos, open_child=False)

    def active_item(self):
        return self.rows[self.active][1]

    def row_at(self, x, y):
        for pos, (row, _) in enumerate(self.rows):
            rx, ry = row.winfo_rootx(), row.winfo_rooty()
            if rx <= x < rx + row.winfo_width() and ry <= y < ry + row.winfo_height():
                return pos
        return None

    # ---- 실행
    def activate(self, pos, by_key=False):
        item = self.rows[pos][1]
        if item["kind"] == "submenu":
            self.open_child(pos)
            if by_key:
                self.bar.key_target = self.child
                self.child.move(1)
            return

        # 메뉴를 먼저 화면에서 없앤 뒤 실행한다 (대화상자가 뜨는 명령이 많다).
        self.bar.close()
        self.bar.update_idletasks()

        if item["kind"] == "radio":
            item["variable"].set(item["value"])
        if item.get("func"):
            item["func"]()

    # ---- 하위 메뉴
    def open_child(self, pos):
        if self.child is not None and self.child_pos == pos:
            return
        self.close_child()
        row, item = self.rows[pos]
        x = row.winfo_rootx() + row.winfo_width()
        y = row.winfo_rooty() - 4
        self.child = Dropdown(self.bar, item["items"], x, y, parent=self)
        self.child_pos = pos

    def close_child(self):
        if self.child is not None:
            self.child.vanish()
            self.child = None
            self.child_pos = None

    # ---- 닫기
    def vanish(self):
        self.close_child()
        try:
            self.place_forget()
            self.destroy()
        except tk.TclError:
            pass
