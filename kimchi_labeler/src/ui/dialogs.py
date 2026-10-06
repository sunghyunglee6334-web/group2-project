"""보조 창: Validation 결과, 진행현황, Class 통계, 단축키 안내."""
import tkinter as tk
from tkinter import ttk

from ..config import CLASS_NAMES
from ..validation.validator import critical_count, summarize
from .style import FONT_MONO, SCENE_LABELS, SUB_TEXT, class_label

HELP_TEXT = """\
마우스
  [새 BBox 그리기] 모드 : 왼쪽 드래그 = 새 BBox, 클릭 = BBox 선택
  [선택 이동] 모드      : BBox 안을 드래그 = 이동, 모서리/변 핸들 드래그 = 크기 조절
  [Pan] 모드            : 왼쪽 드래그 = 화면 이동
  오른쪽/가운데 드래그  : 어느 모드에서나 화면 이동
  휠                    : 마우스 위치 기준 Zoom

단축키
  W 새 BBox 그리기   V 선택 이동   H 라벨 숨기기/보이기
  A/←  이전   D/→ 다음   N 다음 미완료   Space 저장 후 다음   Ctrl+S 저장
  0~6  Class 선택(선택된 BBox 가 있으면 Class 변경, 4 는 사용 불가)
  Del  선택 BBox 삭제    Ctrl+Z Undo    Esc 선택 해제
  F Fit   +/- Zoom      P PASS   E EDITED   R REVIEW
  Ctrl+O RAW 폴더 열기   Ctrl+Q 종료   F1 단축키 보기

메뉴
  Alt+F 파일   Alt+V 보기   Alt+T 도구   Alt+Q 검수   Alt+S 통계   Alt+H 도움말   F10 첫 메뉴
  메뉴가 열려 있을 때: ↑↓ 항목 이동, ←→ 옆 메뉴, Enter 실행, Esc 닫기
"""

SEVERITY_COLORS = {"CRITICAL": "#dc2626", "REVIEW": "#c2410c", "INFO": "#4b5563"}


def text_popup(root, title, text):
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("780x540")

    box = tk.Text(win, wrap="none", font=FONT_MONO)
    box.insert("1.0", text)
    box.configure(state=tk.DISABLED)
    box.pack(fill=tk.BOTH, expand=True)
    return win


def validation_window(root, issues, image_count, report_path, on_jump):
    """Validation 결과 표. 행을 더블클릭하면 on_jump(이미지 상대경로)."""
    win = tk.Toplevel(root)
    win.title("Validation 결과 - 행을 더블클릭하면 그 이미지로 이동")
    win.geometry("980x560")

    # 요약
    parts = [f"검사 {image_count}장", f"CRITICAL {critical_count(issues)}건"]
    summary = summarize(issues)
    for severity in ("CRITICAL", "REVIEW", "INFO"):
        for code, n in summary.get(severity, {}).items():
            parts.append(f"{code} {n}")

    tk.Label(win, text="   ·   ".join(parts), wraplength=950, justify=tk.LEFT,
             padx=6, pady=6).pack(anchor="w")
    tk.Label(win, text=f"보고서: {report_path}", fg=SUB_TEXT, padx=6).pack(anchor="w")

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

    scroll = tk.Scrollbar(win, command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    table.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

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
