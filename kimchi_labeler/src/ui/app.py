"""조각김치 이물검출 라벨링 프로그램 - 메인 창.

화면만 담당한다. BBox 편집과 저장 규칙은 session.LabelSession 이 한다.

  panels.py        위젯 배치
  canvas_editor.py 이미지 / BBox 그리기와 마우스 편집
  menubar.py       메뉴 막대 (tk.Menu 잔상 문제 때문에 직접 만듦)
  dialogs.py       Validation 결과, 통계, 단축키 안내 창
"""
import importlib.util
import shutil
import signal
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image

from ..bbox.canvas_editor import CanvasEditor
from ..bbox.session import FILTERS, LabelSession
from ..bbox.view import ViewTransform
from ..config import (CLASS_COLORS, CLASS_NAMES, IMAGE_EXTS, PROJECT_ROOT, REPORT_DIR,
                      UNUSED_CLASS_IDS, Paths, load_settings, save_settings)
from ..validation.validator import critical_count, validate, write_report
from ..yolo.yolo_io import pixel_to_yolo, yolo_to_pixel
from . import dialogs
from .menubar import SEPARATOR, MenuBar, command, radio, submenu
from .panels import build_main_window
from .style import (BG, EDIT_STATUSES, MODE_CURSORS, SCENE_FROM_LABEL, SCENE_LABELS,
                    STATUS_COLORS, STATUS_MARK, TEXT, class_label, highlight_only)

MODE_MESSAGES = {
    "draw": "새 BBox 그리기: 빈 곳을 드래그하세요 (클릭하면 BBox 선택)",
    "select": "선택 이동: BBox 안을 드래그하면 이동, 모서리/변 핸들로 크기 조절",
    "pan": "Pan: 드래그로 화면 이동",
}


class LabelApp(CanvasEditor):
    def __init__(self, root, session):
        self.root = root
        self.s = session
        self.view = ViewTransform()

        self.pyramid = []           # 원본, 1/2, 1/4 이미지
        self.photo = None           # Canvas 에 올린 PhotoImage (지우면 화면에서 사라짐)
        self.selected = None        # 선택된 BBox 번호
        self.drag = None            # 마우스 드래그 상태
        self.pan_last = None
        self.fit_mode = True
        self.mode = "draw"
        self.hide_labels = False
        self._loading = False       # 화면 값을 채우는 중에는 '변경됨'으로 보지 않는다

        root.title("조각김치 이물검출 라벨링 프로그램")
        root.geometry("1480x900")
        root.minsize(1200, 720)
        root.configure(bg=BG)
        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")     # 콤보박스, 표 모양을 OS 와 상관없이 같게

        # 콤보박스에서 값을 고르면 글자가 선택(파란/회색 배경)된 채로 남는다. 칠하지 않게 한다.
        style.map("TCombobox",
                  fieldbackground=[("readonly", "white")],
                  selectbackground=[("readonly", "white"), ("!focus", "white")],
                  selectforeground=[("readonly", TEXT), ("!focus", TEXT)])
        def clear(event):
            event.widget.after_idle(event.widget.selection_clear)

        root.bind_class("TCombobox", "<<ComboboxSelected>>", clear, add="+")
        root.bind_class("TCombobox", "<FocusIn>", clear, add="+")
        root.bind_class("TCombobox", "<FocusOut>", clear, add="+")

        self.filter_var = tk.StringVar(value="전체")
        self.build_menu()
        build_main_window(self)
        self.bind_canvas()
        self.bind_keys()
        self.refresh_people()

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.set_mode("draw")
        self.refresh_image_list()
        root.after(80, lambda: self.goto(0, check_dirty=False))

    # ================================================================ 메뉴
    def build_menu(self):
        self.menubar = MenuBar(self.root)
        self.menubar.pack(side=tk.TOP, fill=tk.X)
        tk.Frame(self.root, height=1, bg="#d1d5db").pack(side=tk.TOP, fill=tk.X)

        bar = self.menubar

        bar.add_menu("파일(F)", [
            command("RAW 폴더 열기...", self.open_raw_folder, "Ctrl+O"),
            command("이미지 추가 (연습용)...", self.add_images),
            SEPARATOR,
            command("저장", self.save, "Ctrl+S"),
            command("저장 후 다음", self.save_next, "Space"),
            SEPARATOR,
            command("종료", self.on_close, "Ctrl+Q"),
        ], underline=3)

        filter_items = [radio(name, self.filter_var, name, self.change_filter) for name in FILTERS]
        bar.add_menu("보기(V)", [
            command("Fit to Window", self.fit, "F"),
            command("Zoom In", lambda: self.zoom_center(1.25), "+"),
            command("Zoom Out", lambda: self.zoom_center(0.8), "-"),
            command("라벨 숨기기 / 보이기", self.toggle_labels, "H"),
            SEPARATOR,
            submenu("목록 보기 필터", filter_items),
        ], underline=3)

        bar.add_menu("도구(T)", [
            command("새 BBox 그리기", lambda: self.set_mode("draw"), "W"),
            command("선택 이동 / 크기 조절", lambda: self.set_mode("select"), "V"),
            command("Pan (화면 이동)", lambda: self.set_mode("pan")),
            SEPARATOR,
            command("선택 BBox 삭제", self.delete_selected, "Del"),
            command("Undo", self.undo, "Ctrl+Z"),
            SEPARATOR,
            command("Validation 실행", self.run_validation),
        ], underline=3)

        review_items = [
            command("PASS", lambda: self.set_status("PASS"), "P"),
            command("EDITED", lambda: self.set_status("EDITED"), "E"),
            command("REVIEW", lambda: self.set_status("REVIEW"), "R"),
            command("REVIEWED", lambda: self.set_status("REVIEWED")),
            SEPARATOR,
            command("다음 미완료 이미지로", self.goto_next_unfinished, "N"),
        ]
        for name in ("내 담당-미완료", "내 검수 대상", "REVIEW", "PASS 표본검수"):
            review_items.append(command(f"'{name}' 만 보기", lambda x=name: self.apply_filter(x)))
        bar.add_menu("검수(Q)", review_items, underline=3)

        bar.add_menu("통계(S)", [
            command("진행현황", self.show_progress),
            command("Class 별 BBox 통계", self.show_class_stats),
            command("QA Summary 생성", self.make_qa_summary),
        ], underline=3)

        bar.add_menu("도움말(H)", [
            command("단축키 보기", self.show_shortcuts, "F1"),
            command("프로그램 정보", self.show_about),
        ], underline=4)

    # ================================================================ 단축키
    def bind_keys(self):
        r = self.root

        def guard(func):
            """글자를 입력하는 칸(Entry, 콤보, 메모)에서는 단축키를 무시한다."""
            def handler(event):
                if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)):
                    return None
                func()
                return "break"
            return handler

        def always(func):
            def handler(_event):
                func()
                return "break"
            return handler

        for key in ("a", "A", "<Left>"):
            r.bind(key, guard(self.prev))
        for key in ("d", "D", "<Right>"):
            r.bind(key, guard(self.next))

        r.bind("<space>", guard(self.save_next))
        r.bind("<Delete>", guard(self.delete_selected))
        r.bind("<BackSpace>", guard(self.delete_selected))
        r.bind("<Escape>", guard(self.clear_selection))

        # Caps Lock 이 켜져 있으면 대문자로 들어오므로 둘 다 묶는다.
        for letter, func in (("s", self.save), ("z", self.undo),
                             ("q", self.on_close), ("o", self.open_raw_folder)):
            r.bind(f"<Control-{letter}>", always(func))
            r.bind(f"<Control-{letter.upper()}>", always(func))
        r.bind("<F1>", always(self.show_shortcuts))

        letters = {
            "f": self.fit,
            "w": lambda: self.set_mode("draw"),
            "v": lambda: self.set_mode("select"),
            "h": self.toggle_labels,
            "n": self.goto_next_unfinished,
            "p": lambda: self.set_status("PASS"),
            "e": lambda: self.set_status("EDITED"),
            "r": lambda: self.set_status("REVIEW"),
        }
        for key, func in letters.items():
            r.bind(key, guard(func))
            r.bind(key.upper(), guard(func))

        r.bind("<plus>", guard(lambda: self.zoom_center(1.25)))
        r.bind("<equal>", guard(lambda: self.zoom_center(1.25)))
        r.bind("<minus>", guard(lambda: self.zoom_center(0.8)))
        r.bind("<KP_Add>", guard(lambda: self.zoom_center(1.25)))         # 숫자 키패드
        r.bind("<KP_Subtract>", guard(lambda: self.zoom_center(0.8)))

        for cid in CLASS_NAMES:
            r.bind(str(cid), guard(lambda c=cid: self.pick_class(c)))
            r.bind(f"<KP_{cid}>", guard(lambda c=cid: self.pick_class(c)))

    # ================================================================ 모드
    def set_mode(self, mode):
        self.mode = mode
        highlight_only(self.mode_buttons[mode], self.tool_buttons)   # 단축키(W, V)로 바꿔도 표시
        self.canvas.configure(cursor=MODE_CURSORS[mode])
        self.status_bar.set(MODE_MESSAGES[mode])
        if self.s.cur:
            self.draw_boxes()

    def toggle_labels(self):
        self.hide_labels = not self.hide_labels
        self.hide_btn.configure(text="보이기(H)" if self.hide_labels else "숨김(H)")
        highlight_only(self.hide_btn, self.tool_buttons)
        self.draw_boxes()

    # ================================================================ 이미지 목록
    def _list_text(self, key):
        row = self.s.manifest.get(key)
        return f"{STATUS_MARK.get(row['status'], '?')} {row['image_name']}"

    def _list_color(self, key):
        return STATUS_COLORS.get(self.s.manifest.get(key)["status"], TEXT)

    def refresh_image_list(self):
        lb = self.img_list
        lb.delete(0, tk.END)
        for i, key in enumerate(self.s.view_keys):
            lb.insert(tk.END, self._list_text(key))
            lb.itemconfig(i, fg=self._list_color(key))
        self.list_title.set(f"이미지 목록 ({self.s.total})")

    def update_list_item(self, i):
        key = self.s.view_keys[i]
        self.img_list.delete(i)
        self.img_list.insert(i, self._list_text(key))
        self.img_list.itemconfig(i, fg=self._list_color(key))

    def highlight_list(self):
        lb = self.img_list
        lb.selection_clear(0, tk.END)
        if self.s.total:
            lb.selection_set(self.s.index)
            lb.see(self.s.index)

    def on_image_list_select(self, _event):
        selection = self.img_list.curselection()
        if selection and selection[0] != self.s.index:
            self.goto(selection[0])
            self.highlight_list()
        self.canvas.focus_set()

    # ================================================================ 이미지 이동
    def confirm_leave(self):
        """저장 안 한 변경이 있으면 묻는다. True 면 다른 이미지로 가도 된다."""
        if not self.s.is_dirty():
            return True
        answer = messagebox.askyesnocancel(
            "저장하지 않은 변경",
            "이 이미지에 저장하지 않은 변경이 있습니다.\n저장할까요?\n"
            "(예: 저장 후 이동 / 아니오: 버리고 이동 / 취소: 머무르기)",
        )
        if answer is None:
            return False
        if answer:
            return self.save()
        return True

    def goto(self, index, check_dirty=True):
        if self.s.total == 0:
            self.show_empty_view()
            return
        if check_dirty and not self.confirm_leave():
            self.highlight_list()
            return

        self.status_bar.set("이미지 불러오는 중...")
        self.root.update_idletasks()
        try:
            cur = self.s.load(index)
            img = Image.open(cur.rec.raw_image(self.s.paths))
            img.load()
            if img.mode != "RGB":
                img = img.convert("RGB")
        except Exception as e:
            # 이전 이미지 위에 새 라벨이 겹쳐 보이지 않도록 화면을 비운다.
            self.show_empty_view(f"이미지를 열 수 없습니다: {self.s.view_keys[index]}")
            self.highlight_list()
            messagebox.showerror("불러오기 실패", str(e))
            self.status_bar.set(f"불러오기 실패: {e}")
            return

        self.make_pyramid(img)
        self.selected = None
        self.drag = None
        self.load_meta()
        self.highlight_list()
        self.fit()

        source = "WORK 저장본" if cur.from_work else "RAW 원본"
        self.status_bar.set(f"불러옴: {cur.rec.rel_image}  ({source})")

    def show_empty_view(self, message=None):
        """보여 줄 이미지가 없을 때. 이전 이미지의 정보가 남지 않게 모두 비운다."""
        self.canvas.delete("all")
        self.pyramid = []
        self.photo = None
        self.s.cur = None
        self.selected = None
        self.drag = None

        self.head_var.set(message or f"'{self.s.filter_name}' 에 해당하는 이미지가 없습니다")
        self.sub_var.set("")
        self.zoom_var.set("")
        self.warn_var.set("")
        self.info_var.set("")
        self.box_list.delete(0, tk.END)
        self.refresh_box_info()

    def load_meta(self):
        """Manifest 의 상태, Scene, 메모를 오른쪽 칸에 채운다."""
        self._loading = True
        row = self.s.manifest.get(self.s.current_key)

        status = row["status"]
        self.status_var.set(status if status in EDIT_STATUSES else "PASS")
        self.scene_var.set(SCENE_LABELS.get(row["scene_type"], row["scene_type"]))
        self.issue_var.set(row["issue"])
        self.reviewer_var.set(row["reviewer"])
        self.note_text.delete("1.0", tk.END)
        self.note_text.insert("1.0", row["note"])
        self.note_text.edit_modified(False)

        self._loading = False
        self.s.meta_dirty = False
        self.refresh_info()

    def prev(self):
        if self.s.index > 0:
            self.goto(self.s.index - 1)
        else:
            self.status_bar.set("첫 번째 이미지입니다.")

    def next(self):
        if self.s.index < self.s.total - 1:
            self.goto(self.s.index + 1)
        else:
            self.status_bar.set("마지막 이미지입니다.")

    def goto_next_unfinished(self):
        i = self.s.next_unfinished(self.s.index) if self.s.total else None
        if i is None:
            messagebox.showinfo("완료", f"'{self.s.filter_name}' 보기에 미완료(PENDING) 이미지가 없습니다.")
        else:
            self.goto(i)

    def apply_filter(self, name):
        self.filter_var.set(name)
        self.change_filter()

    def change_filter(self):
        if not self.confirm_leave():
            self.filter_var.set(self.s.filter_name)
            return
        n = self.s.set_filter(self.filter_var.get())
        self.refresh_image_list()
        self.canvas.focus_set()
        self.status_bar.set(f"보기: {self.s.filter_name} ({n}장)")
        self.goto(0, check_dirty=False)

    # ================================================================ 오른쪽 정보 갱신
    def refresh_box_list(self):
        lb = self.box_list
        lb.delete(0, tk.END)
        for i, box in enumerate(self.s.cur.boxes):
            name = CLASS_NAMES.get(box.cls, "범위 밖")
            lb.insert(tk.END, f"{i + 1:>2} | {box.cls} {name[:7]:<7} | {box.w:.0f}x{box.h:.0f}")
            color = "#dc2626" if box.cls in UNUSED_CLASS_IDS else CLASS_COLORS.get(box.cls, "#ff0000")
            lb.itemconfig(i, fg=color)

        if self.selected is not None and self.selected < len(self.s.cur.boxes):
            lb.selection_set(self.selected)
            lb.see(self.selected)

    def refresh_box_info(self):
        cur = self.s.cur
        if self.selected is None or not cur or self.selected >= len(cur.boxes):
            for var in self.info_vars.values():
                var.set("")
            self.px_var.set("BBox 를 클릭하면 표시됩니다")
            return

        box = cur.boxes[self.selected]
        cls, cx, cy, w, h = pixel_to_yolo(box, cur.width, cur.height)
        self.info_vars["cls"].set(class_label(cls))
        self.info_vars["cx"].set(f"{cx:.4f}")
        self.info_vars["cy"].set(f"{cy:.4f}")
        self.info_vars["w"].set(f"{w:.4f}")
        self.info_vars["h"].set(f"{h:.4f}")

        nb = box.normalized()
        self.px_var.set(f"#{self.selected + 1}  픽셀 ({nb.x1:.0f},{nb.y1:.0f})-({nb.x2:.0f},{nb.y2:.0f})  "
                        f"{nb.w:.0f}x{nb.h:.0f}")

    def refresh_info(self):
        cur = self.s.cur
        if not cur:
            return
        row = self.s.manifest.get(cur.rec.rel_image)

        dirty = "  ● 저장 안 됨" if self.s.is_dirty() else ""
        source = "WORK 저장본" if cur.from_work else "RAW 원본"
        self.head_var.set(f"{cur.rec.image_name}    ( {self.s.index + 1} / {self.s.total} ){dirty}")
        self.sub_var.set(f"{cur.rec.source_dataset} / {cur.rec.original_split}   ·   "
                         f"{cur.width}x{cur.height}   ·   라벨: {source}")

        self.info_var.set(
            f"현재 상태: {row['status']}\n"
            f"담당: {row['assignee'] or '-'}   검수: {row['reviewer'] or '-'}\n"
            f"원본 BBox {row['original_bbox_count'] or '?'}개 → 현재 {len(cur.boxes)}개\n"
            f"마지막 저장: {row['updated_at'] or '-'}"
        )

        self.warn_var.set("   ".join("⚠ " + w for w in self.collect_warnings()))

        progress = self.s.progress()
        done = sum(n for status, n in progress.items() if status not in ("PENDING", "WORKING"))
        counts = "  ".join(f"{status}:{n}" for status, n in progress.items())
        self.status_bar.set(f"전체 진행 {done}/{len(self.s.records)}   {counts}")

    def collect_warnings(self):
        cur = self.s.cur
        warnings = list(cur.errors)

        if cur.raw_text is None:
            warnings.append("RAW TXT 없음 → 확인 후 필요한 BBox 를 그리고 저장")
        if any(b.cls in UNUSED_CLASS_IDS for b in cur.boxes):
            warnings.append("Class 4 발견 → 삭제하지 말고 REVIEW 로 보내기")
        if any(b.cls not in CLASS_NAMES for b in cur.boxes):
            warnings.append("0~6 범위 밖 Class 존재")

        for b in cur.boxes:
            nb = b.normalized()
            if nb.x1 < -0.5 or nb.y1 < -0.5 or nb.x2 > cur.width + 0.5 or nb.y2 > cur.height + 0.5:
                warnings.append("이미지 밖으로 나간 BBox 있음 (좌표 범위 오류) → 다시 그리거나 좌표 수정")
                break

        if not cur.boxes:
            warnings.append("BBox 없음: 정말 이물이 없는지 확인 (정상이면 PASS)")
        return warnings

    # ================================================================ BBox 편집
    def after_edit(self):
        """BBox 가 바뀌면 상태를 EDITED 로 바꿔 두고 다시 그린다."""
        if self.s.cur.changed_vs_raw() and self.status_var.get() == "PASS":
            self.status_var.set("EDITED")
        self.draw_boxes()
        self.refresh_info()

    def on_box_list_select(self, _event):
        selection = self.box_list.curselection()
        if not selection:
            return
        self.canvas.focus_set()
        self.selected = selection[0]
        self.select_class_of(self.selected)
        self.draw_boxes()

    def clear_selection(self):
        self.selected = None
        self.draw_boxes()

    def select_class_of(self, i):
        """BBox 를 고르면 Class 선택 칸도 그 BBox 의 Class 로 맞춘다."""
        self.class_var.set(self.s.cur.boxes[i].cls)
        self.sync_class_widgets()

    def sync_class_widgets(self):
        cid = self.class_var.get()
        self.class_combo_var.set(class_label(cid))
        self.class_swatch.configure(bg=CLASS_COLORS.get(cid, "#ff0000"))

    def on_class_combo(self, _event):
        cid = int(self.class_combo_var.get().split(".")[0])
        self.canvas.focus_set()
        self.pick_class(cid)

    def pick_class(self, cid):
        if cid in UNUSED_CLASS_IDS:
            messagebox.showwarning("Class 4", "Class 4(고무장갑)는 사용하지 않는 Class 입니다.\n"
                                              "발견된 경우 삭제하지 말고 REVIEW 로 보내세요.")
            self.sync_class_widgets()
            return

        self.class_var.set(cid)
        self.sync_class_widgets()

        cur = self.s.cur
        if self.selected is not None and cur and cur.boxes[self.selected].cls != cid:
            self.s.set_box_class(self.selected, cid)
            self.after_edit()

    def apply_box_entries(self):
        """오른쪽 X/Y/너비/높이 칸의 YOLO 좌표를 선택 BBox 에 적용한다."""
        cur = self.s.cur
        if self.selected is None or not cur:
            self.status_bar.set("먼저 BBox 를 선택하세요.")
            return

        try:
            cx, cy, w, h = (float(self.info_vars[k].get()) for k in ("cx", "cy", "w", "h"))
        except ValueError:
            messagebox.showerror("좌표", "숫자(0~1)를 입력하세요.")
            return

        if not all(0 <= v <= 1 for v in (cx, cy, w, h)) or w <= 0 or h <= 0:
            messagebox.showerror("좌표", "YOLO 좌표는 0~1 사이, 너비·높이는 0보다 커야 합니다.")
            return

        box = yolo_to_pixel(cur.boxes[self.selected].cls, cx, cy, w, h, cur.width, cur.height)
        if self.s.replace_box(self.selected, box):
            self.after_edit()
            self.canvas.focus_set()
        else:
            messagebox.showerror("좌표", "BBox 가 너무 작아 적용하지 않았습니다.")

    def delete_selected(self):
        if self.selected is None or not self.s.cur:
            self.status_bar.set("삭제할 BBox 를 먼저 선택하세요.")
            return
        self.s.delete_box(self.selected)
        self.selected = None
        self.after_edit()

    def undo(self):
        if self.s.cur and self.s.undo():
            self.selected = None
            self.after_edit()

    # ================================================================ 상태 / 메모
    def set_status(self, status):
        self.status_var.set(status)
        self.mark_meta_dirty()

    def mark_meta_dirty(self):
        if not self._loading and self.s.cur:
            self.s.meta_dirty = True
            self.refresh_info()

    def on_scene_select(self, _event):
        self.mark_meta_dirty()
        self.canvas.focus_set()

    def on_note_modified(self, _event):
        if self.note_text.edit_modified():
            self.note_text.edit_modified(False)
            self.mark_meta_dirty()

    # ================================================================ 작업자
    def refresh_people(self):
        team = list(load_settings().get("team", []))
        for row in self.s.manifest.rows.values():
            for key in ("assignee", "reviewer"):
                if row[key] and row[key] not in team:
                    team.append(row[key])
        if self.s.worker and self.s.worker not in team:
            team.insert(0, self.s.worker)

        self.worker_combo.configure(values=team)
        self.reviewer_combo.configure(values=[""] + team)

    def on_worker_change(self):
        name = self.worker_var.get().strip()
        if not name or name == self.s.worker:
            return

        self.s.worker = name
        settings = load_settings()
        settings["worker"] = name
        save_settings(settings)

        self.refresh_people()
        self.canvas.focus_set()
        self.status_bar.set(f"작업자를 '{name}' 으로 바꿨습니다.")
        if self.s.filter_name != "전체":
            self.change_filter()

    # ================================================================ 저장
    def save(self):
        cur = self.s.cur
        if not cur:
            return False

        status = self.status_var.get()
        row = self.s.manifest.get(self.s.current_key)

        if status == "REVIEWED" and row["assignee"] == self.s.worker:
            ok = messagebox.askyesno("교차검수", "본인이 작업한 이미지를 REVIEWED 로 바꾸려 합니다.\n"
                                             "교차검수는 다른 사람이 해야 합니다. 계속할까요?")
            if not ok:
                return False

        if status in ("PASS", "REVIEWED") and any(b.cls in UNUSED_CLASS_IDS for b in cur.boxes):
            messagebox.showwarning("Class 4", "Class 4 가 남아 있어 REVIEW 로 저장합니다.")
            status = "REVIEW"

        # 메모는 여러 줄을 ' / ' 로 이어서 CSV 한 칸에 넣는다.
        lines = self.note_text.get("1.0", "end-1c").splitlines()
        note = " / ".join(line.strip() for line in lines if line.strip())
        scene = SCENE_FROM_LABEL.get(self.scene_var.get(), "")

        try:
            applied = self.s.save(status, scene, note, self.issue_var.get().strip(),
                                  reviewer=self.reviewer_var.get().strip())
        except Exception as e:
            messagebox.showerror("저장 실패", f"저장하지 못했습니다. 이동하지 마세요.\n{e}")
            self.status_bar.set(f"저장 실패: {e}")
            return False

        self.load_meta()
        self.update_list_item(self.s.index)
        self.highlight_list()
        self.draw_boxes()

        if applied != status:
            self.status_bar.set(f"라벨이 원본과 달라 {status} → {applied} 로 저장했습니다.")
        else:
            self.status_bar.set(f"저장 완료: {cur.rec.image_name} [{applied}]")
        return True

    def save_next(self):
        if not self.save():
            return
        if self.s.index < self.s.total - 1:
            self.goto(self.s.index + 1, check_dirty=False)
        else:
            messagebox.showinfo("완료", "현재 보기의 마지막 이미지까지 저장했습니다.")

    # ================================================================ QA / 통계
    def run_validation(self):
        self.status_bar.set("Validation 실행 중...")
        self.root.update_idletasks()

        issues = validate(self.s.paths, use_work=True, records=self.s.records)
        out = REPORT_DIR / f"validation_{datetime.now():%Y%m%d_%H%M%S}.csv"
        write_report(issues, out)

        dialogs.validation_window(self.root, issues, len(self.s.records), out, self.jump_to)
        self.status_bar.set(f"Validation 완료 - CRITICAL {critical_count(issues)}건, 보고서 {out.name}")

    def jump_to(self, rel_image):
        if rel_image not in self.s.by_key:
            messagebox.showinfo("이동", "이미지가 없는 항목입니다 (짝 없는 TXT 등).")
            return

        if self.s.index_of(rel_image) is None:
            # 지금 필터에 없는 이미지면 '전체' 로 바꿔서 연다.
            if not self.confirm_leave():
                return
            self.filter_var.set("전체")
            self.s.set_filter("전체")
            self.refresh_image_list()
            self.goto(self.s.index_of(rel_image), check_dirty=False)
        else:
            self.goto(self.s.index_of(rel_image))
        self.root.lift()

    def show_progress(self):
        text = dialogs.progress_text(self.s.manifest, self.s.records)
        dialogs.text_popup(self.root, "진행현황", text)

    def show_class_stats(self):
        text = dialogs.class_stats_text(self.s.class_counts())
        dialogs.text_popup(self.root, "Class 별 BBox 통계", text)

    def make_qa_summary(self):
        # scripts/05_qa_summary.py 는 파일명이 숫자로 시작해서 import 문으로는 못 부른다.
        path = PROJECT_ROOT / "scripts" / "05_qa_summary.py"
        spec = importlib.util.spec_from_file_location("qa_summary", path)
        qa = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qa)

        self.status_bar.set("QA Summary 생성 중...")
        self.root.update_idletasks()

        text = qa.build(self.s.paths)
        out = REPORT_DIR / "qa_summary.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

        dialogs.text_popup(self.root, f"QA Summary  ({out})", text)
        self.status_bar.set(f"QA Summary 저장: {out}")

    def show_shortcuts(self):
        dialogs.text_popup(self.root, "단축키와 사용법", dialogs.HELP_TEXT)

    def show_about(self):
        messagebox.showinfo("프로그램 정보",
                            "조각김치 이물검출 라벨링 프로그램 (교과 7)\n\n"
                            f"RAW : {self.s.paths.raw}\nWORK: {self.s.paths.work}\n\n"
                            "본 데이터는 교육용 100% 가상 생성 데이터이며 NDA 대상입니다.")

    # ================================================================ 파일
    def on_close(self):
        if self.confirm_leave():
            self.menubar.close()
            self.root.destroy()

    def reload_session(self, session, select=None):
        self.s = session
        self.filter_var.set("전체")
        self.refresh_people()
        self.refresh_image_list()
        index = session.index_of(select) if select else 0
        self.goto(index or 0, check_dirty=False)

    def open_raw_folder(self):
        """다른 RAW 폴더를 연다. WORK 는 RAW 폴더 이름별로 따로 만든다."""
        if not self.confirm_leave():
            return
        chosen = filedialog.askdirectory(title="RAW 데이터 폴더 선택 (이미지가 들어 있는 상위 폴더)",
                                         initialdir=str(self.s.paths.raw.parent))
        if not chosen:
            return
        try:
            session = open_session(chosen, self.s.worker)
        except (SystemExit, Exception) as e:
            messagebox.showerror("폴더 열기 실패", str(e))
            return

        self.reload_session(session)
        self.status_bar.set(f"RAW: {session.paths.raw}   WORK: {session.paths.work}")

    def add_images(self):
        """연습용: 사진을 현재 RAW 의 '추가이미지/images/train' 으로 복사한다.
        RAW 스냅샷이 있는 실제 프로젝트 폴더에서는 RAW 를 바꾸면 안 되므로 막는다."""
        if (self.s.paths.work / "raw_checksums.csv").exists():
            messagebox.showerror("이미지 추가 불가",
                                 "이 폴더는 RAW 스냅샷이 기록된 실제 프로젝트 데이터입니다.\n"
                                 "RAW 는 수정할 수 없습니다. 연습용 폴더에서만 사용하세요.")
            return
        if not self.confirm_leave():
            return

        files = filedialog.askopenfilenames(
            title="추가할 사진 선택 (연습용)",
            filetypes=[("이미지", "*.jpg *.jpeg *.png *.JPG *.JPEG *.PNG")],
        )
        if not files:
            return

        img_dir = self.s.paths.raw / "추가이미지" / "images" / "train"
        lbl_dir = self.s.paths.raw / "추가이미지" / "labels" / "train"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        first = None
        added = 0
        for name in files:
            src = Path(name)
            if src.suffix.lower() not in IMAGE_EXTS:
                continue

            # 같은 이름이 있으면 _1, _2 ... 를 붙인다.
            dst = img_dir / src.name
            n = 1
            while dst.exists():
                dst = img_dir / f"{src.stem}_{n}{src.suffix}"
                n += 1
            shutil.copy2(src, dst)

            txt = src.with_suffix(".txt")
            if txt.exists():
                shutil.copy2(txt, lbl_dir / (dst.stem + ".txt"))

            added += 1
            if first is None:
                first = dst.relative_to(self.s.paths.raw).as_posix()

        self.reload_session(LabelSession(self.s.paths, self.s.worker), select=first)
        messagebox.showinfo("이미지 추가", f"{added}장을 추가했습니다.\n위치: {img_dir}\n"
                                        "라벨이 없는 사진은 BBox 를 그린 뒤 저장하세요.")


# ==================================================================== 실행
def open_session(raw, worker, work=None):
    """RAW 폴더로 세션을 만든다. work 가 없으면 data/work_<RAW폴더이름> 을 쓰고 settings 에 기억한다."""
    raw_path = Path(raw).expanduser().resolve()
    if work is None:
        work = str(PROJECT_ROOT / "data" / f"work_{raw_path.name}")

    paths = Paths(raw_path, work)
    session = LabelSession(paths, worker)       # RAW 가 이상하거나 이미지가 없으면 SystemExit

    settings = load_settings()
    settings["raw_root"] = str(raw_path)
    settings["work_root"] = str(paths.work)
    save_settings(settings)
    return session


def ask_worker(root, worker):
    settings = load_settings()
    worker = worker or settings.get("worker") or ""
    if worker:
        return worker

    worker = simpledialog.askstring("작업자", "작업자 이름(이니셜)을 입력하세요:", parent=root) or ""
    worker = worker.strip()
    if worker:
        settings["worker"] = worker
        save_settings(settings)
    return worker


def ask_session(root, raw, work, worker):
    """명령줄 --raw 또는 settings 의 RAW 로 열어 보고, 안 되면 폴더 선택 창을 띄운다. 취소하면 None."""
    try:
        if raw:
            # 폴더 선택 창으로 연 것과 똑같이 WORK 는 data/work_<RAW폴더이름>, settings 에 기억
            return open_session(raw, worker, work)
        return LabelSession(Paths(None, work), worker)
    except (SystemExit, Exception) as e:
        messagebox.showinfo("RAW 폴더 선택", f"{e}\n\nRAW 데이터 폴더를 선택하세요.")

    while True:
        chosen = filedialog.askdirectory(title="RAW 데이터 폴더 선택 (이미지가 들어 있는 상위 폴더)")
        if not chosen:
            return None
        try:
            return open_session(chosen, worker, work)
        except (SystemExit, Exception) as e:
            messagebox.showerror("폴더 열기 실패", f"{e}\n\n다른 폴더를 선택하세요.")


def run(raw=None, work=None, worker=None):
    root = tk.Tk()
    root.withdraw()

    worker = ask_worker(root, worker)
    if not worker:
        root.destroy()
        return

    session = ask_session(root, raw, work, worker)
    if session is None:
        root.destroy()
        return

    root.deiconify()
    app = LabelApp(root, session)

    # Ctrl+C 도 저장 확인을 거쳐 종료. mainloop 중에는 Python 이 시그널을 못 받으니 주기적으로 깨운다.
    signal.signal(signal.SIGINT, lambda *args: root.after(0, app.on_close))

    def tick():
        root.after(250, tick)

    tick()
    root.mainloop()
