"""보조 창: Validation 결과, 진행현황, Class 통계, 단축키 안내."""
import tkinter as tk
from tkinter import ttk

from ..config import CLASS_NAMES
from ..validation.validator import critical_count, summarize
from .style import (FONT_CAPTION, FONT_MONO, FONT_SMALL, FONT_TITLE, SCENE_LABELS,
                    SEPARATOR, SURFACE, TEXT, TEXT2, TEXT3, class_label)
from .widgets import Card, RoundButton, flat_entry

HELP_TEXT = """\
마우스
  [그리기] (W)        왼쪽 드래그 = 새 BBox, 클릭 = BBox 선택
  [박스 편집] (V)     BBox 안을 드래그 = BBox 이동, 모서리/변 핸들 드래그 = 크기 조절
  [화면 이동]         왼쪽 드래그 = 보는 위치만 이동 (한 번 더 누르거나 Esc 면 그리기로)
  오른쪽/가운데 드래그  어느 모드에서나 화면 이동
  휠                  마우스 위치 기준 Zoom
  미니맵              확대하면 오른쪽 아래에 나타남. 누르면 그 위치로 이동

확대 / 축소 (이미지 아래 ( − 배율 + | 맞춤 100% ) 막대)
  + / -     Zoom In / Out      F   Fit (화면에 맞춤)

단축키
  W 그리기   V 박스 편집   H 라벨 숨기기/보이기
  A/←/↑  이전   D/→/↓ 다음   N 다음 미완료   Space 저장 후 다음   Ctrl+S 저장
  0~6  Class 선택(선택된 BBox 가 있으면 Class 변경, 4 는 사용 불가)
  Del  선택 BBox 삭제    Ctrl+Z Undo    Esc 선택 해제 (화면 이동 중이면 그리기로)
  P PASS   E EDITED   R REVIEW
  Ctrl+O 폴더 열기   Ctrl+Q 종료   F1 단축키 보기

한글 입력 (이슈 · 노트 · 작업자 · 검수자 칸)
  Shift+Space 또는 한/영 키, 또는 이슈 · 노트 옆 [영문] 버튼 → [한글]
  WSL 에서 Windows 한글 입력기가 안 될 때 쓰는 내장 두벌식 입력기입니다.

메뉴 (맨 위 '조각김치 라벨링 ⌄' = 파일,  '⋯' = 나머지)
  Alt+F 파일   Alt+V 보기   Alt+T 도구   Alt+Q 검수   Alt+S 통계   Alt+H 도움말   F10 파일 메뉴
  메뉴가 열려 있을 때: ↑↓ 항목 이동, ←→ 옆 메뉴, Enter 실행, Esc 닫기
"""

SEVERITY_COLORS = {"CRITICAL": "#D70015", "REVIEW": "#C93400", "INFO": "#6E6E73"}


def text_popup(root, title, text):
    win = tk.Toplevel(root, bg=SURFACE)
    win.title(title)
    win.geometry("820x580")

    tk.Label(win, text=title, bg=SURFACE, fg=TEXT, font=FONT_TITLE, anchor="w").pack(
        fill=tk.X, padx=20, pady=(16, 8))
    tk.Frame(win, height=1, bg=SEPARATOR).pack(fill=tk.X)

    foot = tk.Frame(win, bg=SURFACE, padx=20, pady=14)
    foot.pack(side=tk.BOTTOM, fill=tk.X)
    RoundButton(foot, "닫기", win.destroy, variant="primary", height=44, padx=28).pack(side=tk.RIGHT)

    holder = tk.Frame(win, bg=SURFACE)
    holder.pack(fill=tk.BOTH, expand=True)
    box = tk.Text(holder, wrap="none", font=FONT_MONO, bg=SURFACE, fg=TEXT, relief=tk.FLAT, bd=0,
                  padx=20, pady=14, highlightthickness=0, spacing1=2, spacing3=2)
    scroll = ttk.Scrollbar(holder, orient=tk.VERTICAL, command=box.yview)
    box.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    box.pack(fill=tk.BOTH, expand=True)
    box.insert("1.0", text)
    box.configure(state=tk.DISABLED)
    win.bind("<Escape>", lambda e: win.destroy())
    return win


def ask_text(root, title, message, hint="", ime=None, initial=""):
    """한글 입력이 되는 한 줄 입력 창. 확인이면 글자, 취소면 None."""
    result = {"value": None}
    win = tk.Toplevel(root, bg=SURFACE)
    win.title(title)
    win.resizable(False, False)

    body = tk.Frame(win, bg=SURFACE, padx=24, pady=22)
    body.pack(fill=tk.BOTH, expand=True)
    tk.Label(body, text=message, bg=SURFACE, fg=TEXT, font=FONT_TITLE, anchor="w").pack(fill=tk.X)
    if hint:
        tk.Label(body, text=hint, bg=SURFACE, fg=TEXT2, font=FONT_SMALL, anchor="w").pack(
            fill=tk.X, pady=(4, 0))

    var = tk.StringVar(value=initial)
    row = tk.Frame(body, bg=SURFACE)
    row.pack(fill=tk.X, pady=(16, 0))
    box = Card(row, fill="#F2F4F6", radius=12, padx=14, pady=10, width=300)
    box.pack(side=tk.LEFT, fill=tk.X, expand=True)
    e = flat_entry(box.body, var, width=24, font="KBodyBold")
    e.pack(fill=tk.X)

    if ime is not None:
        ime.attach(e)
        btn = RoundButton(row, "영문", ime.toggle, variant="gray", height=40, padx=14)
        btn.pack(side=tk.LEFT, padx=(8, 0))
        ime.on_change(lambda k: (btn.set_text("한글" if k else "영문"), btn.set_active(k)))

    def ok(_e=None):
        if ime is not None:
            ime.commit()
        result["value"] = var.get()
        win.destroy()

    foot = tk.Frame(win, bg=SURFACE, padx=24, pady=18)
    foot.pack(fill=tk.X)
    foot.columnconfigure(0, weight=1, uniform="b")
    foot.columnconfigure(1, weight=2, uniform="b")
    RoundButton(foot, "취소", win.destroy, variant="gray", height=48, radius=14).grid(row=0, column=0, sticky="ew", padx=(0, 8))
    RoundButton(foot, "확인", ok, variant="primary", height=48, radius=14).grid(row=0, column=1, sticky="ew")

    e.bind("<Return>", ok)
    win.bind("<Escape>", lambda _e: win.destroy())
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"+{(sw - win.winfo_reqwidth()) // 2}+{(sh - win.winfo_reqheight()) // 3}")
    win.deiconify()
    win.lift()
    e.focus_force()
    try:
        win.grab_set()
    except tk.TclError:
        pass
    root.wait_window(win)
    return result["value"]


def validation_window(root, issues, image_count, report_path, on_jump):
    """Validation 결과 표. 행을 더블클릭하면 on_jump(이미지 상대경로)."""
    win = tk.Toplevel(root, bg=SURFACE)
    win.title("Validation 결과")
    win.geometry("1020x600")

    crit = critical_count(issues)
    head = tk.Frame(win, bg=SURFACE, padx=20, pady=14)
    head.pack(fill=tk.X)
    tk.Label(head, text="Validation 결과", bg=SURFACE, fg=TEXT, font=FONT_TITLE).pack(side=tk.LEFT)
    tk.Label(head, text=("  CRITICAL 0건 · 통과" if crit == 0 else f"  CRITICAL {crit}건"),
             bg=SURFACE, fg="#248A3D" if crit == 0 else "#D70015", font=FONT_TITLE).pack(side=tk.LEFT)
    tk.Label(head, text="행을 더블클릭하면 그 이미지로 이동", bg=SURFACE, fg=TEXT3,
             font=FONT_SMALL).pack(side=tk.RIGHT)

    # 요약
    parts = [f"검사 {image_count}장", f"CRITICAL {critical_count(issues)}건"]
    summary = summarize(issues)
    for severity in ("CRITICAL", "REVIEW", "INFO"):
        for code, n in summary.get(severity, {}).items():
            parts.append(f"{code} {n}")

    tk.Label(win, text="   ·   ".join(parts), wraplength=980, justify=tk.LEFT, bg=SURFACE, fg=TEXT2,
             font=FONT_SMALL, padx=20).pack(anchor="w")
    tk.Label(win, text=f"보고서  {report_path}", bg=SURFACE, fg=TEXT3, font=FONT_CAPTION,
             padx=20).pack(anchor="w", pady=(2, 8))

    # 결과 표
    columns = ("severity", "code", "file", "line", "message")
    widths = (80, 120, 380, 50, 330)

    table = ttk.Treeview(win, columns=columns, show="headings")
    for col, width in zip(columns, widths):
        table.heading(col, text=col)
        table.column(col, width=width, anchor="w")
    for severity, color in SEVERITY_COLORS.items():
        table.tag_configure(severity, foreground=color)

    for issue in issues:
        values = (issue.severity, issue.code, issue.rel_path, issue.line, issue.message)
        table.insert("", tk.END, values=values, tags=(issue.severity,))

    scroll = ttk.Scrollbar(win, orient=tk.VERTICAL, command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    table.pack(fill=tk.BOTH, expand=True, padx=(20, 0), pady=(0, 16))

    # 더블클릭 -> 이미지로 이동
    def jump(_event):
        item = table.focus()
        if item:
            on_jump(table.item(item, "values")[2])

    table.bind("<Double-1>", jump)
    return win


def progress_text(manifest, records):
    lines = ["[상태별]"]
    for status, n in manifest.count_by("status").items():
        lines.append(f"  {status or '(빈칸)'}: {n}")

    # 담당자별 전체 / 미완료
    lines += ["", "[담당자별: 전체 / 미완료]"]
    per_worker = {}
    for row in manifest.rows.values():
        name = row["assignee"] or "(미배정)"
        total, left = per_worker.get(name, (0, 0))
        per_worker[name] = (total + 1, left + (row["status"] in ("PENDING", "WORKING")))
    for name, (total, left) in sorted(per_worker.items()):
        lines.append(f"  {name}: {total}장 / 미완료 {left}장")

    lines += ["", "[Scene Type]"]
    for code, n in manifest.count_by("scene_type").items():
        lines.append(f"  {SCENE_LABELS.get(code, code)}: {n}")

    lines += ["", "[Dataset / split]"]
    per_set = {}
    for rec in records:
        key = f"{rec.source_dataset}/{rec.original_split}"
        per_set[key] = per_set.get(key, 0) + 1
    for key, n in sorted(per_set.items()):
        lines.append(f"  {key}: {n}")

    return "\n".join(lines)


def class_stats_text(counts):
    total = sum(counts.values()) or 1
    lines = ["현재 저장 기준(WORK, 없으면 RAW) Class 별 BBox 수", ""]
    for cid in sorted(set(CLASS_NAMES) | set(counts)):
        n = counts.get(cid, 0)
        bar = "█" * round(40 * n / total)
        lines.append(f"  {class_label(cid):<26} {n:>5}  {bar}")
    lines += ["", f"  합계 {sum(counts.values())}"]
    return "\n".join(lines)
