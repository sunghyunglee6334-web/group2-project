"""화면 배치.

LabelApp 이 쓰는 위젯을 만들어 app 의 속성으로 붙인다.
여기서는 '어디에 무엇을 놓을지'만 정하고, 버튼을 눌렀을 때의 동작은 app 의 메서드가 한다.

  ┌ 메뉴 막대 ──────────────────────────────────────────────────────────┐
  │ 이미지 목록 │        이미지 (Canvas)        │ Class / BBox │ 작업 상태 │
  ├ 보기 도구 ─── 라벨 도구 ─────────────────── 이미지 이동 및 저장 ──────┤
  └ 상태바 ─────────────────────────────────────────────────────────────┘
"""
import tkinter as tk
from tkinter import ttk

from ..bbox.session import FILTERS
from ..config import ACTIVE_CLASS_IDS, CLASS_COLORS, CLASS_NAMES, SCENE_TYPES
from .style import (BG, BLUE, BLUE_DARK, BORDER, CANVAS_BG, EDIT_STATUSES, FONT, FONT_BOLD,
                    FONT_HEADER, FONT_MONO, FONT_SMALL, GREEN, GREEN_DARK, PANEL_BG, SCENE_LABELS,
                    STATUS_COLORS, SUB_TEXT, TEXT, WARN_TEXT, action_button, big_button, class_label,
                    group_box)


def build_main_window(app):
    root = app.root

    # 아래쪽(상태바, 도구 막대)을 먼저 붙여야 창을 줄여도 버튼이 가려지지 않는다.
    app.status_bar = tk.StringVar(value="준비")
    status = tk.Label(
        root,
        textvariable=app.status_bar,
        anchor="w",
        relief=tk.SUNKEN,
        bd=1,
        bg=BG,
        padx=6,
        pady=2,
    )
    status.pack(side=tk.BOTTOM, fill=tk.X)

    build_bottom_tools(app, root)

    # 경고 줄은 세 영역 아래에 가로로 길게 둔다.
    # 그래야 이미지 목록, 이미지, 오른쪽 칸의 아래쪽 선이 한 줄로 맞는다.
    app.warn_var = tk.StringVar()
    warn = tk.Label(root, textvariable=app.warn_var, bg=BG, fg=WARN_TEXT, anchor="w",
                    justify=tk.LEFT, wraplength=1400, padx=10, pady=2)
    warn.pack(side=tk.BOTTOM, fill=tk.X)

    panes = tk.PanedWindow(root, orient=tk.HORIZONTAL, bg=BG, bd=0, sashwidth=6, sashrelief=tk.FLAT)
    panes.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))

    left = tk.Frame(panes, bg=BG)
    build_image_list(app, left)
    panes.add(left, minsize=200, width=250, stretch="never")

    center = tk.Frame(panes, bg=BG)
    build_center(app, center)
    panes.add(center, minsize=400, stretch="always")

    right = tk.Frame(panes, bg=BG)
    column_a = tk.Frame(right, bg=BG, width=260)
    column_b = tk.Frame(right, bg=BG, width=240)
    column_a.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 4))
    column_b.pack(side=tk.LEFT, fill=tk.Y)
    column_a.pack_propagate(False)
    column_b.pack_propagate(False)
    build_class_panel(app, column_a)
    build_status_panel(app, column_b)
    panes.add(right, minsize=510, stretch="never")


# 1. 왼쪽: 이미지 목록
def build_image_list(app, parent):
    app.list_title = tk.StringVar(value="이미지 목록")

    frame = group_box(parent, "")
    frame.configure(labelwidget=tk.Label(frame, textvariable=app.list_title, bg=PANEL_BG,
                                         fg=TEXT, font=FONT_BOLD))
    frame.pack(fill=tk.BOTH, expand=True)

    filter_combo = ttk.Combobox(
        frame,
        textvariable=app.filter_var,
        values=list(FILTERS),
        state="readonly",
    )
    filter_combo.pack(fill=tk.X, pady=(0, 4))
    filter_combo.bind("<<ComboboxSelected>>", lambda e: app.change_filter())

    holder = tk.Frame(frame, bg=PANEL_BG)
    holder.pack(fill=tk.BOTH, expand=True)

    app.img_list = tk.Listbox(
        holder,
        exportselection=False,
        activestyle="none",
        font=FONT_MONO,
        selectbackground="#dbeafe",
        selectforeground=TEXT,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=BORDER,
        takefocus=0,
    )
    scroll = tk.Scrollbar(holder, command=app.img_list.yview)
    app.img_list.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    app.img_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    app.img_list.bind("<<ListboxSelect>>", app.on_image_list_select)

    legend = tk.Label(frame, text="○대기 ✓PASS ✎EDITED !REVIEW ✔검수완료",
                      bg=PANEL_BG, fg=SUB_TEXT, font=FONT_SMALL)
    legend.pack(anchor="w", pady=(4, 0))


# 2. 가운데: 파일명, 이미지, 경고
def build_center(app, parent):
    head = tk.Frame(parent, bg=BG)
    head.pack(fill=tk.X)

    app.head_var = tk.StringVar()
    tk.Label(head, textvariable=app.head_var, bg=BG, fg=TEXT,
             font=FONT_HEADER).pack(side=tk.LEFT, padx=4)

    app.zoom_var = tk.StringVar()
    tk.Label(head, textvariable=app.zoom_var, bg=BG, fg=SUB_TEXT).pack(side=tk.RIGHT, padx=6)

    app.sub_var = tk.StringVar()
    tk.Label(parent, textvariable=app.sub_var, bg=BG, fg=SUB_TEXT).pack(anchor="w", padx=4)

    app.canvas = tk.Canvas(parent, bg=CANVAS_BG, highlightthickness=0, cursor="crosshair")
    app.canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))


# 3. 오른쪽 1열: Class 선택, BBox 정보, BBox 목록
def build_class_panel(app, parent):
    first = ACTIVE_CLASS_IDS[0]

    # 3-1. Class 선택
    frame = group_box(parent, "Class 선택 (숫자키 0~6)")
    frame.pack(fill=tk.X)

    app.class_var = tk.IntVar(value=first)
    app.class_combo_var = tk.StringVar(value=class_label(first))

    class_combo = ttk.Combobox(
        frame,
        textvariable=app.class_combo_var,
        values=[class_label(cid) for cid in CLASS_NAMES],
        state="readonly",
    )
    class_combo.pack(fill=tk.X)
    class_combo.bind("<<ComboboxSelected>>", app.on_class_combo)

    app.class_swatch = tk.Label(frame, text="", height=1, bg=CLASS_COLORS[first])
    app.class_swatch.pack(fill=tk.X, pady=(4, 0))

    # 3-2. 현재 선택된 BBox 정보 (YOLO 좌표를 직접 고칠 수 있다)
    frame = group_box(parent, "현재 선택된 BBox 정보")
    frame.pack(fill=tk.X, pady=6)
    frame.columnconfigure(1, weight=1)

    app.info_vars = {key: tk.StringVar() for key in ("cls", "cx", "cy", "w", "h")}
    app.info_entries = {}
    rows = [("Class", "cls"), ("X(중심)", "cx"), ("Y(중심)", "cy"), ("너비", "w"), ("높이", "h")]

    for row, (text, key) in enumerate(rows):
        tk.Label(frame, text=text, bg=PANEL_BG).grid(row=row, column=0, sticky="w", pady=2)

        entry = tk.Entry(frame, textvariable=app.info_vars[key], width=16, relief=tk.SOLID, bd=1)
        if key == "cls":
            entry.configure(state="readonly", readonlybackground="white")
        else:
            entry.bind("<Return>", lambda e: app.apply_box_entries())
        entry.grid(row=row, column=1, sticky="ew", padx=(6, 0), pady=2)
        app.info_entries[key] = entry

    app.px_var = tk.StringVar(value="BBox 를 클릭하면 표시됩니다")
    tk.Label(frame, textvariable=app.px_var, bg=PANEL_BG, fg=SUB_TEXT,
             font=FONT_SMALL).grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

    apply_button = tk.Button(frame, text="좌표 적용 (Enter)", command=app.apply_box_entries,
                             takefocus=0)
    apply_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    # 3-3. BBox 목록
    frame = group_box(parent, "BBox 목록")
    frame.pack(fill=tk.BOTH, expand=True)

    app.box_list = tk.Listbox(
        frame,
        exportselection=False,
        activestyle="none",
        font=FONT_MONO,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=BORDER,
        takefocus=0,
    )
    app.box_list.pack(fill=tk.BOTH, expand=True)
    app.box_list.bind("<<ListboxSelect>>", app.on_box_list_select)


# 4. 오른쪽 2열: 작업 상태, Scene Type, 작업자, 파일 정보, 메모
def build_status_panel(app, parent):
    # 4-1. 작업 상태
    frame = group_box(parent, "작업 상태 (P / E / R)")
    frame.pack(fill=tk.X)

    app.status_var = tk.StringVar(value="PASS")
    for status in EDIT_STATUSES:
        button = tk.Radiobutton(
            frame,
            text=status,
            variable=app.status_var,
            value=status,
            command=app.mark_meta_dirty,
            anchor="w",
            fg=STATUS_COLORS[status],
            font=FONT_BOLD,
            bg=PANEL_BG,
            activebackground=PANEL_BG,
            highlightthickness=0,
            takefocus=0,
        )
        button.pack(fill=tk.X)

    # 4-2. Scene Type
    frame = group_box(parent, "Scene Type")
    frame.pack(fill=tk.X, pady=(6, 0))

    app.scene_var = tk.StringVar(value=SCENE_LABELS[""])
    scene_combo = ttk.Combobox(
        frame,
        textvariable=app.scene_var,
        values=[SCENE_LABELS[code] for code in SCENE_TYPES],
        state="readonly",
    )
    scene_combo.pack(fill=tk.X)
    scene_combo.bind("<<ComboboxSelected>>", app.on_scene_select)

    # 4-3. 작업자 / 검수자
    frame = group_box(parent, "작업자 / 검수자")
    frame.pack(fill=tk.X, pady=(6, 0))
    frame.columnconfigure(1, weight=1)

    tk.Label(frame, text="작업자", bg=PANEL_BG).grid(row=0, column=0, sticky="w")
    app.worker_var = tk.StringVar(value=app.s.worker)
    app.worker_combo = ttk.Combobox(frame, textvariable=app.worker_var, width=14)
    app.worker_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=2)
    app.worker_combo.bind("<<ComboboxSelected>>", lambda e: app.on_worker_change())
    app.worker_combo.bind("<Return>", lambda e: app.on_worker_change())

    tk.Label(frame, text="검수자", bg=PANEL_BG).grid(row=1, column=0, sticky="w")
    app.reviewer_var = tk.StringVar()
    app.reviewer_combo = ttk.Combobox(frame, textvariable=app.reviewer_var, width=14)
    app.reviewer_combo.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=2)
    app.reviewer_combo.bind("<<ComboboxSelected>>", lambda e: app.mark_meta_dirty())
    app.reviewer_combo.bind("<KeyRelease>", lambda e: app.mark_meta_dirty())

    # 4-4. 파일 정보
    frame = group_box(parent, "파일 정보")
    frame.pack(fill=tk.X, pady=(6, 0))

    app.info_var = tk.StringVar()
    tk.Label(frame, textvariable=app.info_var, bg=PANEL_BG, justify=tk.LEFT,
             wraplength=220).pack(anchor="w")

    # 4-5. 이슈 / 메모
    frame = group_box(parent, "이슈 / 메모")
    frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    tk.Label(frame, text="Issue (문제)", bg=PANEL_BG, fg=SUB_TEXT).pack(anchor="w")
    app.issue_var = tk.StringVar()
    tk.Entry(frame, textvariable=app.issue_var, relief=tk.SOLID, bd=1).pack(fill=tk.X)
    app.issue_var.trace_add("write", lambda *args: app.mark_meta_dirty())

    tk.Label(frame, text="Note (판단·수정 이유)", bg=PANEL_BG, fg=SUB_TEXT).pack(anchor="w", pady=(4, 0))
    app.note_text = tk.Text(
        frame,
        height=4,
        wrap="word",
        font=FONT,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=BORDER,
    )
    app.note_text.pack(fill=tk.BOTH, expand=True)
    app.note_text.bind("<<Modified>>", app.on_note_modified)


# 5. 아래: 보기 도구, 라벨 도구, 이동/저장
def build_bottom_tools(app, root):
    bar = tk.Frame(root, bg=BG, padx=6, pady=4)
    bar.pack(side=tk.BOTTOM, fill=tk.X)
    app.mode_buttons = {}
    app.tool_buttons = tools = []      # 이 중 마지막으로 누른 버튼 하나만 파란색

    # 5-1. 보기 도구
    frame = group_box(bar, "보기 도구")
    frame.pack(side=tk.LEFT)

    action_button(frame, "Zoom In", lambda: app.zoom_center(1.25), tools).pack(side=tk.LEFT, padx=2)
    action_button(frame, "Zoom Out", lambda: app.zoom_center(0.8), tools).pack(side=tk.LEFT, padx=2)
    action_button(frame, "Fit", app.fit, tools).pack(side=tk.LEFT, padx=2)

    app.mode_buttons["pan"] = action_button(frame, "Pan", lambda: app.set_mode("pan"), tools)
    app.mode_buttons["pan"].pack(side=tk.LEFT, padx=2)

    app.hide_btn = action_button(frame, "숨김(H)", app.toggle_labels, tools)
    app.hide_btn.pack(side=tk.LEFT, padx=2)

    # 5-2. 라벨 도구
    frame = group_box(bar, "라벨 도구")
    frame.pack(side=tk.LEFT, padx=6)

    app.mode_buttons["draw"] = action_button(frame, "새 BBox (W)", lambda: app.set_mode("draw"), tools)
    app.mode_buttons["draw"].pack(side=tk.LEFT, padx=2)

    app.mode_buttons["select"] = action_button(frame, "선택 이동 (V)", lambda: app.set_mode("select"),
                                                 tools)
    app.mode_buttons["select"].pack(side=tk.LEFT, padx=2)

    action_button(frame, "삭제 (Del)", app.delete_selected, tools).pack(side=tk.LEFT, padx=2)
    action_button(frame, "Undo", app.undo, tools).pack(side=tk.LEFT, padx=2)
    action_button(frame, "Validation", app.run_validation, tools).pack(side=tk.LEFT, padx=2)

    # 5-3. 이미지 이동 및 저장
    frame = group_box(bar, "이미지 이동 및 저장")
    frame.pack(side=tk.RIGHT)

    for text, command in (("◀ 이전", app.prev), ("다음 ▶", app.next)):
        button = tk.Button(frame, text=text, command=command, font=FONT_BOLD,
                           padx=10, pady=6, takefocus=0)
        button.pack(side=tk.LEFT, padx=2)

    big_button(frame, "저장", app.save, GREEN, GREEN_DARK).pack(side=tk.LEFT, padx=(6, 2))
    big_button(frame, "저장 후 다음", app.save_next, BLUE, BLUE_DARK).pack(side=tk.LEFT, padx=2)
