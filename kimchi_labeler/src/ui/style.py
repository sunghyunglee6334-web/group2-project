"""화면에서 같이 쓰는 색, 글꼴, 표시 문구와 위젯 생성 함수."""
import tkinter as tk

from ..config import CLASS_NAMES, UNUSED_CLASS_IDS

# 색
BG = "#f3f4f6"
PANEL_BG = "#f3f4f6"
CANVAS_BG = "#1f2937"
BORDER = "#d1d5db"
TEXT = "#111827"
SUB_TEXT = "#4b5563"
WARN_TEXT = "#dc2626"
BLUE = "#2563eb"
BLUE_DARK = "#1e40af"
GREEN = "#16a34a"
GREEN_DARK = "#15803d"
TOOL_BG = "#e5e7eb"
TOOL_ACTIVE_BG = "#d1d5db"

# 글꼴
FONT = ("", 10)
FONT_BOLD = ("", 10, "bold")
FONT_SMALL = ("", 8)
FONT_HEADER = ("", 12, "bold")
FONT_BIG_BUTTON = ("", 11, "bold")
FONT_MONO = ("Consolas", 10)

# 작업 상태 표시
EDIT_STATUSES = ["PASS", "EDITED", "REVIEW", "REVIEWED"]

STATUS_COLORS = {
    "PENDING": "#6b7280",
    "WORKING": "#6b7280",
    "PASS": "#15803d",
    "EDITED": "#c2410c",
    "REVIEW": "#dc2626",
    "REVIEWED": "#1d4ed8",
    "FINAL": "#7c3aed",
}

STATUS_MARK = {
    "PENDING": "○",
    "WORKING": "…",
    "PASS": "✓",
    "EDITED": "✎",
    "REVIEW": "!",
    "REVIEWED": "✔",
    "FINAL": "■",
}

# Scene Type 은 화면에는 한글, 저장은 영문 코드
SCENE_LABELS = {
    "": "(선택 안 함)",
    "kimchi_with_target": "김치 + 대상 객체",
    "normal_kimchi": "정상 김치",
    "object_only": "대상 객체 단독",
    "other_review": "판단 어려움 (other_review)",
}
SCENE_FROM_LABEL = {label: code for code, label in SCENE_LABELS.items()}

# BBox 크기 조절 핸들
HANDLE_RADIUS = 7           # 클릭으로 인정하는 반경 (화면 px)
HANDLE_CURSORS = {
    "nw": "top_left_corner",
    "ne": "top_right_corner",
    "sw": "bottom_left_corner",
    "se": "bottom_right_corner",
    "n": "top_side",
    "s": "bottom_side",
    "w": "left_side",
    "e": "right_side",
}

MODE_CURSORS = {"draw": "crosshair", "select": "arrow", "pan": "fleur"}


def class_label(cid):
    """콤보박스와 BBox 정보 칸에 쓰는 Class 표시 문구."""
    name = CLASS_NAMES.get(cid, "범위 밖")
    text = f"{cid}. {name}"
    if cid in UNUSED_CLASS_IDS:
        text += " - 사용 안 함"
    return text


def tool_button(parent, text, command):
    """아래 도구 막대의 작은 버튼."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=TOOL_BG,
        activebackground=TOOL_ACTIVE_BG,
        relief=tk.GROOVE,
        padx=8,
        pady=3,
        takefocus=0,
    )


def paint_active(button, on):
    """도구 버튼을 파란색(켜짐) 또는 기본 회색으로 칠한다."""
    if on:
        button.configure(bg=BLUE, fg="white", activebackground=BLUE_DARK,
                         activeforeground="white")
    else:
        button.configure(bg=TOOL_BG, fg=TEXT, activebackground=TOOL_ACTIVE_BG,
                         activeforeground=TEXT)


def highlight_only(button, group):
    """group 안에서 button 하나만 파란색, 나머지는 회색."""
    for other in group:
        paint_active(other, other is button)


def action_button(parent, text, command, group):
    """도구 막대 버튼. 누르면 같은 group 에서 이 버튼만 파란색이 된다."""
    button = tool_button(parent, text, None)
    group.append(button)

    def run():
        highlight_only(button, group)
        button.update_idletasks()          # Validation 처럼 오래 걸려도 파란색이 먼저 보이게
        command()

    button.configure(command=run)
    return button


def big_button(parent, text, command, color, active_color):
    """저장 / 저장 후 다음 처럼 눈에 띄어야 하는 버튼."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg="white",
        activebackground=active_color,
        activeforeground="white",
        font=FONT_BIG_BUTTON,
        relief=tk.FLAT,
        padx=14,
        pady=6,
        takefocus=0,
    )


def group_box(parent, text):
    """제목이 붙은 테두리 영역."""
    return tk.LabelFrame(
        parent,
        text=text,
        bg=PANEL_BG,
        fg=TEXT,
        font=FONT_BOLD,
        padx=6,
        pady=4,
        bd=1,
        relief=tk.GROOVE,
    )
