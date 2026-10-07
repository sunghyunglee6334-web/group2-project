"""화면 공통 디자인 값 (색, 글꼴, 상태 표시 문구).

디자인 방향: 토스 앱처럼
  - 연한 회색 바탕 위에 둥근 흰 카드, 선은 거의 쓰지 않는다
  - 제목은 크고 굵게, 보조 설명은 연한 회색
  - 강조색은 토스 파랑 하나, 선택된 것은 연한 파랑 바탕
  - 이미지는 어두운 바탕 위에 (BBox 색이 잘 보이게)

글꼴은 이름 붙은 Tk 글꼴(named font)로 만든다. init_fonts(root) 를 창을 만들기 전에 한 번 부른다.
PC 에 있는 한글 글꼴 중 가장 좋은 것을 자동으로 고른다.
"""
import tkinter as tk
from tkinter import font as tkfont

from ..config import CLASS_NAMES, UNUSED_CLASS_IDS

# ---------------------------------------------------------------- 색 (토스 팔레트)
BG = "#F2F4F6"              # 창 바탕 (연한 회색)
CARD = "#FFFFFF"            # 카드 바탕
SURFACE = CARD
FILL = "#F2F4F6"            # 카드 안 회색 칸 (입력칸, 타일, 보조 버튼)
FILL_HOVER = "#E5E8EB"
FILL_PRESS = "#D1D6DB"
LINE = "#E5E8EB"            # 아주 옅은 구분선 / 흰 버튼 테두리
SEPARATOR = LINE
BORDER = "#D1D6DB"

TEXT = "#191F28"            # 제목·본문
TEXT2 = "#4E5968"           # 버튼 글자, 중요한 보조 글자
TEXT3 = "#8B95A1"           # 설명 글자
TEXT4 = "#B0B8C1"           # 흐린 글자 (대기, 비활성)

BLUE = "#3182F6"            # 토스 파랑
BLUE_HOVER = "#2272EB"
BLUE_PRESS = "#1B64DA"
BLUE_SOFT = "#E8F3FF"       # 선택된 행·버튼 바탕
BLUE_SOFT_HOVER = "#D9EBFF"
ACCENT, ACCENT_HOVER, ACCENT_PRESS, ACCENT_SOFT = BLUE, BLUE_HOVER, BLUE_PRESS, BLUE_SOFT

GREEN = "#00C473"
ORANGE = "#FF9F0A"
ORANGE_TEXT = "#E07B00"
RED = "#F04452"
PURPLE = "#8B5CF6"

WARN_BG = "#FFF8E1"
WARN_TEXT = "#9A6400"

CANVAS_BG = "#191F28"       # 이미지 뒤 바탕

# 예전 이름 (다른 모듈 호환)
PANEL_BG = CARD
SIDEBAR = CARD
SUB_TEXT = TEXT3

# ---------------------------------------------------------------- 글꼴 (named font 이름)
FONT = "KBody"
FONT_BOLD = "KBodyBold"
FONT_SMALL = "KSmall"
FONT_SMALL_BOLD = "KSmallBold"
FONT_CAPTION = "KCaption"
FONT_CAPTION_BOLD = "KCaptionBold"
FONT_TITLE = "KTitle"           # 카드 제목 (Class, 검수 상태 ...)
FONT_HEADER = "KHeader"         # 파일명
FONT_APP = "KApp"               # 맨 위 '조각김치 라벨링'
FONT_BIG = "KBig"               # '3 / 16장 완료' 의 큰 숫자
FONT_LARGE = "KLarge"           # Zoom 막대의 − +
FONT_BUTTON = "KButton"
FONT_CTA = "KCta"               # '저장하고 다음 장' 큰 버튼
FONT_MONO = "KMono"
FONT_MONO_BOLD = "KMonoBold"
FONT_BOX = "KBox"               # 캔버스 BBox 이름표
FONT_TOAST = "KToast"           # Zoom 배율 크게 표시

UI_FAMILIES = ["Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "맑은 고딕",
               "Noto Sans CJK KR", "Noto Sans KR", "NanumBarunGothic", "NanumSquare", "NanumGothic",
               "나눔고딕", "Noto Sans CJK JP", "WenQuanYi Zen Hei", "Segoe UI", "Helvetica Neue",
               "DejaVu Sans"]
MONO_FAMILIES = ["D2Coding", "SF Mono", "Menlo", "Consolas", "NanumGothicCoding",
                 "Noto Sans Mono CJK KR", "DejaVu Sans Mono", "Courier New"]


def _pick(available, wanted):
    lower = {f.lower(): f for f in available}
    for name in wanted:
        if name.lower() in lower:
            return lower[name.lower()]
    return "TkDefaultFont"


_FONTS = []      # Font 객체를 잡아 둔다 (버리면 Python 이 Tk 글꼴을 지워 버린다)


def init_fonts(root):
    """한글이 깨지지 않는 글꼴을 골라 named font 를 만든다."""
    families = set(tkfont.families(root))
    ui = _pick(families, UI_FAMILIES)
    mono = _pick(families, MONO_FAMILIES)
    specs = {
        FONT: (ui, 10, "normal"),
        FONT_BOLD: (ui, 10, "bold"),
        FONT_SMALL: (ui, 9, "normal"),
        FONT_SMALL_BOLD: (ui, 9, "bold"),
        FONT_CAPTION: (ui, 8, "normal"),
        FONT_CAPTION_BOLD: (ui, 8, "bold"),
        FONT_TITLE: (ui, 12, "bold"),
        FONT_HEADER: (ui, 15, "bold"),
        FONT_APP: (ui, 18, "bold"),
        FONT_BIG: (ui, 21, "bold"),
        FONT_LARGE: (ui, 15, "normal"),
        FONT_BUTTON: (ui, 10, "bold"),
        FONT_CTA: (ui, 12, "bold"),
        FONT_MONO: (mono, 10, "normal"),
        FONT_MONO_BOLD: (mono, 11, "bold"),
        FONT_BOX: (ui, 9, "bold"),
        FONT_TOAST: (ui, 22, "bold"),
    }
    for name, (family, size, weight) in specs.items():
        try:
            tkfont.Font(root=root, name=name, exists=True).configure(family=family, size=size, weight=weight)
        except tk.TclError:
            _FONTS.append(tkfont.Font(root=root, name=name, family=family, size=size, weight=weight))

    # 기본 위젯(메시지 상자 등)도 같은 글꼴로
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.Font(root=root, name=name, exists=True).configure(family=ui, size=10)
        except tk.TclError:
            pass
    return ui


def setup_ttk(root):
    """표·스크롤바를 밝고 납작한 모양으로."""
    from tkinter import ttk
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # 회색 타일 안에 들어가는 납작한 콤보박스 (작업자 / 검수자)
    style.configure("Tile.TCombobox", padding=(0, 1), relief="flat", borderwidth=0, arrowsize=12,
                    fieldbackground=FILL, background=FILL, foreground=TEXT, arrowcolor=TEXT3,
                    bordercolor=FILL, lightcolor=FILL, darkcolor=FILL, insertcolor=BLUE)
    style.map("Tile.TCombobox", fieldbackground=[("readonly", FILL), ("focus", FILL)],
              background=[("active", FILL), ("pressed", FILL)], bordercolor=[("focus", FILL)],
              lightcolor=[("focus", FILL)], darkcolor=[("focus", FILL)],
              selectbackground=[("!focus", FILL)], selectforeground=[("!focus", TEXT)])
    root.option_add("*TCombobox*Listbox.font", FONT)
    root.option_add("*TCombobox*Listbox.selectBackground", BLUE_SOFT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                    rowheight=28, borderwidth=0, font=FONT)
    style.configure("Treeview.Heading", background=FILL, foreground=TEXT3, relief="flat",
                    font=FONT_SMALL_BOLD, padding=(8, 6))
    style.map("Treeview", background=[("selected", BLUE_SOFT)], foreground=[("selected", TEXT)])

    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", troughcolor=CARD, background=FILL,
                        bordercolor=CARD, lightcolor=FILL, darkcolor=FILL,
                        arrowcolor=TEXT4, relief="flat", gripcount=0, arrowsize=10)
        style.map(f"{orient}.TScrollbar", background=[("active", FILL_PRESS)])
    return style


# ---------------------------------------------------------------- 작업 상태 표시
EDIT_STATUSES = ["PASS", "EDITED", "REVIEW", "REVIEWED"]

STATUS_COLORS = {          # 목록 아이콘·막대 색
    "PENDING": TEXT4,
    "WORKING": TEXT4,
    "PASS": BLUE,
    "EDITED": ORANGE,
    "REVIEW": RED,
    "REVIEWED": GREEN,
    "FINAL": PURPLE,
}
STATUS_TEXT_COLORS = dict(STATUS_COLORS, EDITED=ORANGE_TEXT)   # 글자로 쓸 때 (주황은 조금 진하게)

STATUS_MARK = {
    "PENDING": "○", "WORKING": "◐", "PASS": "✓", "EDITED": "✎",
    "REVIEW": "!", "REVIEWED": "✔", "FINAL": "■",
}

STATUS_KO = {
    "PENDING": "대기",
    "WORKING": "작업 중",
    "PASS": "PASS",
    "EDITED": "수정",
    "REVIEW": "확인 필요",
    "REVIEWED": "검수 완료",
    "FINAL": "최종",
}

# Scene Type 은 화면에는 한글, 저장은 영문 코드
SCENE_LABELS = {
    "": "선택 안 함",
    "kimchi_with_target": "김치 + 대상 객체",
    "normal_kimchi": "정상 김치",
    "object_only": "대상 객체 단독",
    "other_review": "판단 어려움",
}
SCENE_FROM_LABEL = {label: code for code, label in SCENE_LABELS.items()}

# BBox 크기 조절 핸들
HANDLE_RADIUS = 7           # 클릭으로 인정하는 반경 (화면 px)
HANDLE_CURSORS = {
    "nw": "top_left_corner", "ne": "top_right_corner",
    "sw": "bottom_left_corner", "se": "bottom_right_corner",
    "n": "top_side", "s": "bottom_side", "w": "left_side", "e": "right_side",
}

MODE_CURSORS = {"draw": "crosshair", "select": "arrow", "pan": "fleur"}


def class_label(cid):
    """Class 표시 문구."""
    name = CLASS_NAMES.get(cid, "범위 밖")
    text = f"{cid}  {name}"
    if cid in UNUSED_CLASS_IDS:
        text += " (사용 안 함)"
    return text


def text_on(color):
    """색 위에 올릴 글자색 (밝은 색이면 검정, 어두우면 흰색)."""
    try:
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    except (ValueError, TypeError, IndexError):
        return "white"
    return TEXT if (0.299 * r + 0.587 * g + 0.114 * b) > 160 else "white"
