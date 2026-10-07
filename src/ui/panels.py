"""화면 배치 (토스 스타일 카드 레이아웃).

LabelApp 이 쓰는 위젯을 만들어 app 의 속성으로 붙인다.
여기서는 '어디에 무엇을 놓을지'만 정하고, 눌렀을 때의 동작은 app 의 메서드가 한다.

  조각김치 라벨링 ⌄      (상태 메시지)                          [파일 열기] [Validation] [⋯]
  ┌ 작업 현황 ─────┐  ┌ 파일명 ─────────────── ● 저장 안 됨 ┐  ┌ Class ──────────┐
  │ 3 / 16장 완료  │  │ ⚠ 경고                                │  │ ⓪ 나뭇잎·종이류   │
  │ ▬▬ 상태 막대   │  │                                       │  │ ...              │
  └───────────────┘  │          이미지 (어두운 바탕)            │  └─────────────────┘
  ┌ 전체|내 담당|… ┐  │                        [미니맵]        │  ┌ 선택한 BBox ────┐
  │ ① 파일명  PASS │  │       ( − 26% + | 맞춤 100% )          │  │ X  Y  너비  높이  │
  │ ② ...         │  │ [그리기][선택][이동]  ‹ 1/16 ›  [되돌리기][삭제] │  └─────────────────┘
  │               │  └───────────────────────────────────────┘  ┌ 검수 상태 ──────┐
  └───────────────┘                                             │ PASS 수정 …      │
                                                                 │ 장면 · 작업자 …   │
                                                                 │ 메모        [한글] │
                                                                 └─────────────────┘
                                                                 [ 저장 ][ 저장하고 다음 장 → ]
"""
import tkinter as tk
from tkinter import ttk

from ..config import CLASS_COLORS, CLASS_NAMES, UNUSED_CLASS_IDS
from .overlay import CanvasOverlay
from .style import (BG, BLUE, CANVAS_BG, CARD, EDIT_STATUSES, FILL, FONT, FONT_APP, FONT_BIG,
                    FONT_BOLD, FONT_CAPTION, FONT_CTA, FONT_HEADER, FONT_LARGE, FONT_MONO_BOLD,
                    FONT_SMALL, FONT_SMALL_BOLD, FONT_TITLE, SCENE_LABELS, STATUS_KO, TEXT, TEXT2,
                    TEXT3, WARN_BG, WARN_TEXT)
from .widgets import (BarChart, Card, ChoiceGroup, Pill, RichList, RoundButton, ScrollFrame, Tabs,
                      flat_entry, tile)

# 검수 상태 버튼: 선택되면 상태마다 다른 색 (바탕, 글자, 테두리)
STATUS_CHOICE_STYLES = {
    "PASS": ("#E8F3FF", "#3182F6", "#3182F6"),        # 파랑
    "EDITED": ("#FFF4E5", "#E07B00", "#FF9F0A"),      # 주황
    "REVIEW": ("#FFEEF0", "#F04452", "#F04452"),      # 빨강
    "REVIEWED": ("#E6F8EF", "#00A661", "#00C473"),    # 초록
}

TAB_OPTIONS = [("전체", "전체"), ("내 담당", "내 담당"), ("REVIEW", "확인 필요")]
# 선택 = BBox 를 고르고 옮기는 것, 화면 이동 = 이미지(보는 위치)를 옮기는 것 → 이름으로 구분
MODE_OPTIONS = [("draw", "그리기"), ("select", "박스 편집"), ("pan", "화면 이동")]
GAP = 14


def build_main_window(app):
    root = app.root
    root.configure(bg=BG)

    build_header(app, root)

    main = tk.Frame(root, bg=BG)
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
    main.rowconfigure(0, weight=1)
    main.columnconfigure(1, weight=1)

    left = tk.Frame(main, bg=BG, width=300)
    left.grid(row=0, column=0, sticky="ns", padx=(0, GAP))
    left.pack_propagate(False)
    build_left(app, left)

    center = Card(main, expand=True, padx=18, pady=16)
    center.grid(row=0, column=1, sticky="nsew")
    build_center(app, center.body)

    right = tk.Frame(main, bg=BG, width=360)
    right.grid(row=0, column=2, sticky="ns", padx=(GAP, 0))
    right.pack_propagate(False)
    build_right(app, right)


# ==================================================================== 맨 위
def build_header(app, root):
    bar = tk.Frame(root, bg=BG, padx=24, pady=14)
    bar.pack(side=tk.TOP, fill=tk.X)

    app.title_btn = RoundButton(bar, "조각김치 라벨링  ⌄", None, variant="ghost", height=44,
                                font=FONT_APP, padx=10, radius=12, tooltip="파일 메뉴")
    app.title_btn.pack(side=tk.LEFT)
    app.mode_pill = Pill(bar, height=26)
    app.mode_pill.pack(side=tk.LEFT, padx=(6, 0))

    app.status_bar = tk.StringVar(value="")
    tk.Label(bar, textvariable=app.status_bar, bg=BG, fg=TEXT3, font=FONT_SMALL,
             anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(18, 12))

    app.more_btn = RoundButton(bar, "⋯", None, variant="ghost", height=40, width=44, font=FONT_LARGE,
                               tooltip="메뉴: 보기 · 도구 · 검수 · 통계 · 도움말")
    app.more_btn.pack(side=tk.RIGHT, padx=(6, 0))
    RoundButton(bar, "Validation", app.run_validation, variant="white", height=40,
                tooltip="전체 라벨 자동 검사").pack(side=tk.RIGHT, padx=(8, 0))
    RoundButton(bar, "파일 열기", app.add_images, variant="white", height=40,
                tooltip="사진 파일을 골라 추가 (연습용 · 실제 RAW 에서는 막힘)").pack(side=tk.RIGHT, padx=(8, 0))
    RoundButton(bar, "폴더 열기", app.open_raw_folder, variant="white", height=40,
                tooltip="Ctrl+O · 이미지가 들어 있는 RAW 상위 폴더 선택").pack(side=tk.RIGHT)


# ==================================================================== 왼쪽: 작업 현황 + 이미지 목록
def build_left(app, parent):
    hero = Card(parent, padx=22, pady=20)
    hero.pack(fill=tk.X)
    b = hero.body
    tk.Label(b, text="작업 현황", bg=CARD, fg=TEXT2, font=FONT_SMALL_BOLD, anchor="w").pack(fill=tk.X)
    row = tk.Frame(b, bg=CARD)
    row.pack(fill=tk.X, pady=(4, 0))
    app.hero_done = tk.StringVar(value="0")
    app.hero_total = tk.StringVar(value="/ 0장 완료")
    tk.Label(row, textvariable=app.hero_done, bg=CARD, fg=TEXT, font=FONT_BIG).pack(side=tk.LEFT)
    tk.Label(row, textvariable=app.hero_total, bg=CARD, fg=TEXT3, font=FONT_BOLD).pack(
        side=tk.LEFT, padx=(6, 0), pady=(8, 0))
    app.hero_sub = tk.StringVar(value="")
    tk.Label(b, textvariable=app.hero_sub, bg=CARD, fg=TEXT3, font=FONT_SMALL, anchor="w").pack(fill=tk.X)
    app.hero_bars = BarChart(b)
    app.hero_bars.pack(fill=tk.X, pady=(12, 0))

    lst = Card(parent, expand=True, padx=0, pady=6)
    lst.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
    app.tab_var = tk.StringVar(value="전체")
    Tabs(lst.body, TAB_OPTIONS, app.tab_var, command=app.on_tab).pack(fill=tk.X, padx=16)
    app.img_list = RichList(lst.body, app.on_image_pick)
    app.img_list.pack(fill=tk.BOTH, expand=True, pady=(6, 4))


# ==================================================================== 가운데: 이미지
def build_center(app, parent):
    head = tk.Frame(parent, bg=CARD)
    head.pack(fill=tk.X)
    app.head_var = tk.StringVar(value="")
    app.sub_var = tk.StringVar(value="")
    names = tk.Frame(head, bg=CARD)
    names.pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Label(names, textvariable=app.head_var, bg=CARD, fg=TEXT, font=FONT_HEADER, anchor="w").pack(fill=tk.X)
    tk.Label(names, textvariable=app.sub_var, bg=CARD, fg=TEXT3, font=FONT_SMALL, anchor="w").pack(fill=tk.X)
    side = tk.Frame(head, bg=CARD)
    side.pack(side=tk.RIGHT, anchor="n")
    app.dirty_pill = Pill(side, height=30)
    app.dirty_pill.pack(anchor="e")
    app.zoom_var = tk.StringVar()           # 마우스 위치의 원본 좌표 + 배율
    tk.Label(side, textvariable=app.zoom_var, bg=CARD, fg=TEXT3, font=FONT_CAPTION, anchor="e").pack(
        anchor="e", pady=(4, 0))

    # 경고 (있을 때만 show_warn 으로 보인다)
    app.warn_var = tk.StringVar()
    app.warn_card = Card(parent, fill=WARN_BG, radius=12, padx=14, pady=10)
    tk.Label(app.warn_card.body, textvariable=app.warn_var, bg=WARN_BG, fg=WARN_TEXT, font=FONT_SMALL_BOLD,
             anchor="w", justify=tk.LEFT, wraplength=760).pack(fill=tk.X)

    # 아래 막대: 모드 / 이동 / 되돌리기·삭제
    nav = tk.Frame(parent, bg=CARD)
    nav.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
    app.mode_buttons = {}
    tips = {"draw": "W · 드래그로 새 BBox",
            "select": "V · BBox 를 골라 옮기거나 핸들로 크기 조절 (이미지는 안 움직임)",
            "pan": "보는 위치만 옮기기 (BBox 는 안 바뀜) · 한 번 더 누르거나 Esc 면 그리기로"}
    for mode, label in MODE_OPTIONS:
        btn = RoundButton(nav, label, lambda m=mode: app.on_mode_button(m), variant="white", height=40,
                          tooltip=tips[mode])
        btn.pack(side=tk.LEFT, padx=(0, 6))
        app.mode_buttons[mode] = btn

    RoundButton(nav, "삭제", app.delete_selected, variant="danger", height=40,
                tooltip="Del").pack(side=tk.RIGHT)
    RoundButton(nav, "되돌리기", app.undo, variant="gray", height=40,
                tooltip="Ctrl+Z").pack(side=tk.RIGHT, padx=(0, 6))
    app.hide_btn = RoundButton(nav, "라벨 숨김", app.toggle_labels, variant="gray", height=40,
                               tooltip="H")
    app.hide_btn.pack(side=tk.RIGHT, padx=(0, 6))

    move = tk.Frame(nav, bg=CARD)
    move.place(relx=0.5, rely=0.5, anchor="center")
    RoundButton(move, "‹", app.prev, variant="gray", height=40, width=40, font=FONT_LARGE,
                tooltip="A / ←").pack(side=tk.LEFT)
    app.pos_var = tk.StringVar(value="0 / 0")
    tk.Label(move, textvariable=app.pos_var, bg=CARD, fg=TEXT, font=FONT_BOLD, width=10).pack(side=tk.LEFT)
    RoundButton(move, "›", app.next, variant="gray", height=40, width=40, font=FONT_LARGE,
                tooltip="D / →").pack(side=tk.LEFT)

    # 이미지 무대
    app.stage = tk.Frame(parent, bg=CANVAS_BG)
    app.stage.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
    app.canvas = tk.Canvas(app.stage, bg=CANVAS_BG, highlightthickness=0, bd=0, cursor="crosshair")
    app.canvas.pack(fill=tk.BOTH, expand=True)
    app.overlay = CanvasOverlay(app)        # Zoom 막대 · 미니맵 · 배율 토스트 · 둥근 모서리

    # 이미지가 없을 때 안내
    app.empty_frame = tk.Frame(app.stage, bg=CANVAS_BG)
    app.empty_title = tk.Label(app.empty_frame, text="", bg=CANVAS_BG, fg="#FFFFFF", font=FONT_HEADER)
    app.empty_title.pack()
    app.empty_sub = tk.Label(app.empty_frame, text="", bg=CANVAS_BG, fg="#B0B8C1", font=FONT,
                             justify=tk.CENTER)
    app.empty_sub.pack(pady=(8, 16))
    app.empty_button = RoundButton(app.empty_frame, "폴더 열기", app.open_raw_folder, variant="primary",
                                   height=44)
    app.empty_button.pack()


def show_warn(app, on):
    if on and not app.warn_card.winfo_ismapped():
        app.warn_card.pack(fill=tk.X, pady=(12, 0), before=app.stage)
    elif not on and app.warn_card.winfo_ismapped():
        app.warn_card.pack_forget()


# ==================================================================== 오른쪽
def build_right(app, parent):
    # 맨 아래 큰 저장 버튼 (스크롤과 상관없이 항상 보이게 먼저 붙인다)
    cta = tk.Frame(parent, bg=BG)
    cta.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
    cta.columnconfigure(0, weight=1, uniform="cta")
    cta.columnconfigure(1, weight=2, uniform="cta")
    RoundButton(cta, "저장", app.save, variant="soft", height=54, radius=16, font=FONT_CTA,
                tooltip="Ctrl+S").grid(row=0, column=0, sticky="ew", padx=(0, 8))
    RoundButton(cta, "저장하고 다음 장", app.save_next, variant="primary", height=54, radius=16,
                font=FONT_CTA, tooltip="Space").grid(row=0, column=1, sticky="ew")

    scroll = ScrollFrame(parent, bg=BG)
    scroll.pack(fill=tk.BOTH, expand=True)
    body = scroll.body

    build_class_card(app, body)
    build_box_card(app, body)
    build_review_card(app, body)


def card_title(parent, text, right_var=None):
    row = tk.Frame(parent, bg=CARD)
    row.pack(fill=tk.X, pady=(0, 10))
    tk.Label(row, text=text, bg=CARD, fg=TEXT, font=FONT_TITLE).pack(side=tk.LEFT)
    if right_var is not None:
        tk.Label(row, textvariable=right_var, bg=CARD, fg=TEXT3, font=FONT_SMALL_BOLD).pack(side=tk.RIGHT)
    return row


def build_class_card(app, parent):
    card = Card(parent, padx=14, pady=16)
    card.pack(fill=tk.X)
    title = card_title(card.body, "Class")
    title.pack_configure(padx=6)
    tk.Label(title, text="숫자키 0~6", bg=CARD, fg=TEXT3, font=FONT_SMALL_BOLD).pack(side=tk.RIGHT)

    app.class_var = tk.IntVar(value=min(c for c in CLASS_NAMES if c not in UNUSED_CLASS_IDS))
    app.class_ids = list(CLASS_NAMES)
    app.class_list = RichList(card.body, lambda i: app.pick_class(app.class_ids[i]), row_h=40,
                              icon_d=28, two_line=False, pad=0, scroll=False)
    app.class_list.pack(fill=tk.X)


def build_box_card(app, parent):
    card = Card(parent, padx=20, pady=16)
    card.pack(fill=tk.X, pady=(12, 0))
    app.box_title = tk.StringVar(value="")
    card_title(card.body, "선택한 BBox", app.box_title)

    grid = tk.Frame(card.body, bg=CARD)
    grid.pack(fill=tk.X)
    app.info_vars = {key: tk.StringVar() for key in ("cls", "cx", "cy", "w", "h")}
    app.info_entries = {}
    for i, (label, key) in enumerate((("X", "cx"), ("Y", "cy"), ("너비", "w"), ("높이", "h"))):
        grid.columnconfigure(i, weight=1, uniform="tile")
        t, e = tile(grid, label, app.info_vars[key], font=FONT_MONO_BOLD)
        t.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
        e.bind("<Return>", lambda ev: app.apply_box_entries())
        app.info_entries[key] = e

    foot = tk.Frame(card.body, bg=CARD)
    foot.pack(fill=tk.X, pady=(8, 0))
    app.px_var = tk.StringVar(value="")
    tk.Label(foot, textvariable=app.px_var, bg=CARD, fg=TEXT3, font=FONT_CAPTION, anchor="w",
             justify=tk.LEFT, wraplength=220).pack(side=tk.LEFT, fill=tk.X, expand=True)
    RoundButton(foot, "좌표 적용", app.apply_box_entries, variant="soft", height=32, padx=12,
                font=FONT_SMALL_BOLD, tooltip="Enter").pack(side=tk.RIGHT)

    # BBox 목록 (누르면 그 BBox 선택)
    tk.Label(card.body, text="BBox 목록", bg=CARD, fg=TEXT2, font=FONT_SMALL_BOLD, anchor="w").pack(
        fill=tk.X, pady=(14, 2))
    app.box_list = RichList(card.body, app.on_box_pick, row_h=40, icon_d=26, two_line=False, pad=0,
                            title_font=FONT)
    app.box_list.configure(height=4 * 40 + 8)
    app.box_list.pack(fill=tk.X)


def build_review_card(app, parent):
    card = Card(parent, padx=20, pady=16)
    card.pack(fill=tk.X, pady=(12, 0))
    b = card.body
    card_title(b, "검수 상태")

    app.status_var = tk.StringVar(value="PASS")
    ChoiceGroup(b, [(s, STATUS_KO[s]) for s in EDIT_STATUSES], app.status_var,
                command=lambda v: app.mark_meta_dirty(), height=40, styles=STATUS_CHOICE_STYLES).pack(fill=tk.X)

    grid = tk.Frame(b, bg=CARD)
    grid.pack(fill=tk.X, pady=(10, 0))
    grid.columnconfigure(0, weight=1, uniform="who")
    grid.columnconfigure(1, weight=1, uniform="who")

    app.scene_var = tk.StringVar(value=SCENE_LABELS[""])
    app.scene_tile, scene_label = tile(grid, "장면 유형  ⌄", app.scene_var, entry=False)
    app.scene_tile.grid(row=0, column=0, columnspan=2, sticky="ew")
    for w in (app.scene_tile, app.scene_tile.body, *app.scene_tile.body.winfo_children()):
        w.configure(cursor="hand2")
        w.bind("<ButtonRelease-1>", lambda e: app.open_scene_menu(), add="+")

    # 작업자 / 검수자: 팀원 이름을 고르거나 직접 입력 (콤보박스, 원래 동작 그대로)
    app.worker_var = tk.StringVar(value=app.s.worker)
    t, app.worker_combo = combo_tile(grid, "작업자", app.worker_var)
    t.grid(row=1, column=0, sticky="ew", pady=(8, 0), padx=(0, 4))
    app.worker_combo.bind("<<ComboboxSelected>>", lambda e: app.on_worker_change())
    app.worker_combo.bind("<Return>", lambda e: app.on_worker_change())
    app.ime.attach(app.worker_combo)

    app.reviewer_var = tk.StringVar()
    t, app.reviewer_combo = combo_tile(grid, "검수자", app.reviewer_var)
    t.grid(row=1, column=1, sticky="ew", pady=(8, 0), padx=(4, 0))
    app.reviewer_combo.bind("<<ComboboxSelected>>", lambda e: app.mark_meta_dirty())
    app.reviewer_combo.bind("<KeyRelease>", lambda e: app.mark_meta_dirty())
    app.ime.attach(app.reviewer_combo)

    app.info_var = tk.StringVar()
    tk.Label(b, textvariable=app.info_var, bg=CARD, fg=TEXT3, font=FONT_CAPTION, anchor="w",
             justify=tk.LEFT).pack(fill=tk.X, pady=(10, 0))

    build_note_card(app, parent)


def build_note_card(app, parent):
    """이슈 · 노트 (원래 레이아웃처럼 한 묶음). 이름은 크게, 설명은 회색으로."""
    card = Card(parent, padx=20, pady=16)
    card.pack(fill=tk.X, pady=(12, 0))
    b = card.body

    head = card_title(b, "이슈 · 노트")
    app.ime_btn = RoundButton(head, "영문", app.ime.toggle, variant="gray", height=26, padx=12,
                              radius=13, font=FONT_SMALL_BOLD, tooltip="한/영 전환 · Shift+Space 또는 한/영 키")
    app.ime_btn.pack(side=tk.RIGHT)

    def on_ime(korean):
        app.ime_btn.set_text("한글" if korean else "영문")
        app.ime_btn.set_active(korean)
    app.ime.on_change(on_ime)

    def field_label(text, hint):
        row = tk.Frame(b, bg=CARD)
        row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(row, text=text, bg=CARD, fg=TEXT, font=FONT_BOLD).pack(side=tk.LEFT)
        tk.Label(row, text=hint, bg=CARD, fg=TEXT3, font=FONT_SMALL).pack(side=tk.LEFT, padx=(8, 0))

    field_label("이슈", "문제")
    app.issue_var = tk.StringVar()
    box = Card(b, fill=FILL, radius=12, padx=12, pady=9)
    box.pack(fill=tk.X)
    app.issue_entry = flat_entry(box.body, app.issue_var)
    app.issue_entry.pack(fill=tk.X)
    app.issue_var.trace_add("write", lambda *a: app.mark_meta_dirty())
    app.ime.attach(app.issue_entry)

    tk.Frame(b, height=12, bg=CARD).pack()
    field_label("노트", "판단 · 수정 이유")
    memo = Card(b, fill=FILL, radius=12, padx=12, pady=10)
    memo.pack(fill=tk.X)
    app.note_text = tk.Text(memo.body, height=3, wrap="word", font=FONT, bg=FILL, fg=TEXT,
                            insertbackground=BLUE, relief=tk.FLAT, bd=0, padx=0, pady=0,
                            highlightthickness=0, undo=True, selectbackground="#C9E2FF")
    app.note_text.pack(fill=tk.X)
    app.note_text.bind("<<Modified>>", app.on_note_modified)
    app.ime.attach(app.note_text)


def combo_tile(parent, label, var):
    """회색 둥근 칸 안의 납작한 콤보박스 (목록에서 고르거나 직접 입력)."""
    card = Card(parent, fill=FILL, radius=12, padx=12, pady=8)
    tk.Label(card.body, text=label, bg=FILL, fg=TEXT3, font=FONT_CAPTION, anchor="w").pack(fill=tk.X)
    combo = ttk.Combobox(card.body, textvariable=var, style="Tile.TCombobox", font=FONT_BOLD, width=8)
    combo.pack(fill=tk.X, pady=(1, 0))
    return card, combo


def class_rows(app, counts):
    """Class 목록 행 데이터 (오른쪽에 현재 이미지의 BBox 개수)."""
    rows = []
    for cid in app.class_ids:
        unused = cid in UNUSED_CLASS_IDS
        color = CLASS_COLORS.get(cid, "#ff0000")
        n = counts.get(cid, 0)
        rows.append(dict(icon=str(cid), icon_bg="#D1D6DB" if unused else color, title=CLASS_NAMES[cid],
                         right="사용 안 함" if unused else (f"{n}개" if n else ""), right_fg=TEXT3,
                         dim=unused))
    return rows
