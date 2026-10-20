"""오른쪽 'AI 검출 · Auto Label' 카드와 동작.

화면(버튼 · 상태 · 결과 목록 · 캔버스 점선 박스)만 담당한다.
실제 추론과 라벨 생성은 src/inference/bridge.py 의 함수를 부른다 (GUI 에 모델 코드 중복 X).

  ┌ AI 검출 · Auto Label ────────── [더미 연결] ┐
  │ final_best.pt · imgsz 1280 · conf ≥ 0.25     │
  │ [ Detection 실행 ]   [ Auto Label ]           │
  │ ● 검출 3개 (0.8초)                            │
  │ ② 나뭇가지류                         0.91     │   ← 누르면 캔버스에서 강조
  │ ① 플라스틱·돌·금속                   0.64     │
  │ [결과 숨김] [지우기]                          │
  └──────────────────────────────────────────────┘
"""
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox

from ..config import ACTIVE_CLASS_IDS, CLASS_COLORS
from ..inference import bridge
from ..yolo.yolo_io import read_label_file
from .style import (BLUE, CARD, FONT_CAPTION, FONT_SMALL, FONT_SMALL_BOLD, FONT_TITLE, GREEN,
                    ORANGE_TEXT, RED, TEXT, TEXT3, text_on)
from .widgets import Card, Pill, RichList, RoundButton

STATUS_COLOR = {"idle": TEXT3, "busy": BLUE, "ok": GREEN, "warn": ORANGE_TEXT, "error": RED}
SPIN = "◐◓◑◒"


def build_ai_card(app, parent):
    app.ai = AiPanel(app, parent)


class AiPanel:
    def __init__(self, app, parent):
        self.app = app
        self.dets = None            # 현재 이미지의 검출 결과 (None = 아직 실행 안 함)
        self.det_key = None         # 어느 이미지의 결과인지
        self.selected = None
        self.hidden = False
        self.busy = False
        self._build(parent)
        self.on_image_changed()

    # ================================================================ 화면
    def _build(self, parent):
        card = Card(parent, padx=20, pady=16)
        card.pack(fill=tk.X, pady=(0, 12))
        b = card.body

        head = tk.Frame(b, bg=CARD)
        head.pack(fill=tk.X)
        tk.Label(head, text="AI 검출 · Auto Label", bg=CARD, fg=TEXT, font=FONT_TITLE).pack(side=tk.LEFT)
        mode = Pill(head, height=24)
        mode.pack(side=tk.RIGHT)
        if bridge.MODEL_INFO["connected"]:
            mode.set("모델 연결됨", fg=GREEN, bg="#E6F8EF")
        else:
            mode.set("더미 연결", fg=ORANGE_TEXT, bg="#FFF4E5")

        info = bridge.MODEL_INFO
        tk.Label(b, text=f"{info['weight'].split('/')[-1]} · imgsz {info['imgsz']} · conf ≥ {info['conf']}",
                 bg=CARD, fg=TEXT3, font=FONT_CAPTION, anchor="w").pack(fill=tk.X, pady=(4, 10))

        row = tk.Frame(b, bg=CARD)
        row.pack(fill=tk.X)
        row.columnconfigure(0, weight=1, uniform="ai")
        row.columnconfigure(1, weight=1, uniform="ai")
        self.det_btn = RoundButton(row, "Detection 실행", self.on_detection, variant="primary", height=40,
                                   tooltip="현재 이미지에서 이물 검출 (결과는 점선 박스)")
        self.det_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.auto_btn = RoundButton(row, "Auto Label", self.on_auto_label, variant="soft", height=40,
                                    tooltip="검출 결과로 YOLO TXT 후보를 만들고 화면에 올림 → 검수 후 저장")
        self.auto_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(b, textvariable=self.status_var, bg=CARD, fg=TEXT3, font=FONT_SMALL_BOLD,
                                     anchor="w", justify=tk.LEFT, wraplength=300)
        self.status_label.pack(fill=tk.X, pady=(10, 4))

        self.result_list = RichList(b, self.on_pick, row_h=36, icon_d=24, two_line=False, pad=0)
        self.result_list.configure(height=3 * 36 + 8)
        self.result_list.pack(fill=tk.X)

        foot = tk.Frame(b, bg=CARD)
        foot.pack(fill=tk.X, pady=(6, 0))
        self.hide_btn = RoundButton(foot, "결과 숨김", self.toggle_hidden, variant="gray", height=30, padx=12,
                                    font=FONT_SMALL_BOLD)
        self.hide_btn.pack(side=tk.LEFT)
        RoundButton(foot, "지우기", self.clear, variant="gray", height=30, padx=12,
                    font=FONT_SMALL_BOLD).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(foot, text="점선 = AI 결과", bg=CARD, fg=TEXT3, font=FONT_CAPTION).pack(side=tk.RIGHT)

    def set_status(self, text, kind="idle"):
        self.status_var.set(text)
        self.status_label.configure(fg=STATUS_COLOR.get(kind, TEXT3))

    def _set_busy(self, on):
        self.busy = on
        self.det_btn.set_enabled(not on)
        self.auto_btn.set_enabled(not on)

    def _refresh_list(self):
        rows = []
        for d in self.dets or []:
            color = CLASS_COLORS.get(d.class_id, "#ff0000")
            rows.append(dict(icon=str(d.class_id), icon_bg=color, title=d.class_name,
                             right=f"{d.conf:.2f}", right_fg=TEXT))
        self.result_list.set_rows(rows)
        self.result_list.set_selected(self.selected)

    # ================================================================ 이미지가 바뀔 때
    def on_image_changed(self):
        self.dets, self.det_key, self.selected = None, None, None
        self._refresh_list()
        if not self.busy:
            self.set_status("이미지를 열고 [Detection 실행] 을 누르세요")

    def clear(self):
        self.dets, self.selected = None, None
        self._refresh_list()
        self.set_status("결과를 지웠습니다")
        self.app.draw_boxes()

    def toggle_hidden(self):
        self.hidden = not self.hidden
        self.hide_btn.set_text("결과 보기" if self.hidden else "결과 숨김")
        self.hide_btn.set_active(self.hidden)
        self.app.draw_boxes()

    def on_pick(self, i):
        self.selected = i
        self.hidden = False
        self.hide_btn.set_text("결과 숨김")
        self.hide_btn.set_active(False)
        self.result_list.set_selected(i)
        self.app.draw_boxes()

    # ================================================================ 캔버스 (canvas_editor.draw_boxes 에서 부름)
    def draw_on_canvas(self):
        c = self.app.canvas
        c.delete("det")
        if self.hidden or not self.dets or not self.app.s.cur or self.det_key != self.app.s.current_key:
            return
        view = self.app.view
        for i, d in enumerate(self.dets):
            x1, y1 = view.to_canvas(d.x1, d.y1)
            x2, y2 = view.to_canvas(d.x2, d.y2)
            color = CLASS_COLORS.get(d.class_id, "#ff0000")
            sel = i == self.selected
            c.create_rectangle(x1, y1, x2, y2, outline=color, width=3 if sel else 2, dash=(6, 4), tags="det")
            # 이름표는 박스 아래쪽 (사람 라벨 이름표는 위쪽이라 겹치지 않게)
            tid = c.create_text(x1 + 6, y2 + 11, text=f"AI {d.class_name} {d.conf:.2f}", anchor="w",
                                fill=text_on(color), font=FONT_SMALL_BOLD, tags="det")
            bx1, by1, bx2, by2 = c.bbox(tid)
            bg = c.create_rectangle(x1, by1 - 2, bx2 + 6, by2 + 2, fill=color, outline="", tags="det")
            c.tag_lower(bg, tid)

    # ================================================================ 비동기 실행 (화면이 멈추지 않게)
    def _run_async(self, label, func, args, on_done):
        self._set_busy(True)
        q = queue.Queue()
        key = self.app.s.current_key
        start = time.time()

        def work():
            try:
                q.put(("ok", func(*args)))
            except Exception as e:      # 기능 코드 오류도 화면에 메시지로
                q.put(("error", e))

        threading.Thread(target=work, daemon=True).start()

        def poll(n=0):
            try:
                kind, value = q.get_nowait()
            except queue.Empty:
                self.set_status(f"{SPIN[n % 4]}  {label} 중...", "busy")
                self.app.root.after(120, poll, n + 1)
                return
            self._set_busy(False)
            if key != self.app.s.current_key:
                self.set_status("이미지가 바뀌어 결과를 버렸습니다", "warn")
                return
            if kind == "error":
                self.set_status(f"{label} 실패: {value}", "error")
                messagebox.showerror(f"{label} 실패", str(value))
                return
            on_done(value, time.time() - start)

        poll()

    def _ready(self, what):
        if self.busy:
            return None
        cur = self.app.s.cur
        if not cur:
            messagebox.showinfo(what, "먼저 이미지를 여세요.")
            return None
        path = cur.rec.raw_image(self.app.s.paths)
        reason = bridge.check_demo_allowed(path)
        if reason:
            self.set_status(reason, "warn")
            messagebox.showwarning(what, reason)
            return None
        return path

    # ================================================================ Detection
    def on_detection(self, then=None):
        path = self._ready("Detection")
        if path is None:
            return

        def done(dets, sec):
            self.dets, self.det_key, self.selected = dets, self.app.s.current_key, None
            self.hidden = False
            self.hide_btn.set_text("결과 숨김")
            self.hide_btn.set_active(False)
            self._refresh_list()
            if dets:
                self.set_status(f"●  검출 {len(dets)}개  ({sec:.1f}초)", "ok")
            else:
                self.set_status(f"검출된 객체 없음  ({sec:.1f}초)", "warn")
            self.app.draw_boxes()
            if then:
                then()

        self._run_async("Detection", bridge.run_detection, (path,), done)

    # ================================================================ Auto Label
    def on_auto_label(self):
        if self.dets is None or self.det_key != self.app.s.current_key:
            self.on_detection(then=self._auto_label)      # 검출 결과가 없으면 먼저 검출
        else:
            self._auto_label()

    def _auto_label(self):
        path = self._ready("Auto Label")
        if path is None:
            return
        if not self.dets:
            messagebox.showinfo("Auto Label", "검출된 객체가 없어 만들 라벨이 없습니다.")
            return

        out = bridge.candidate_label_path(path)
        overwrite = False
        if out.exists():
            if not messagebox.askyesno("후보 라벨 덮어쓰기", f"이 이미지의 후보 라벨이 이미 있습니다.\n{out}\n\n덮어쓸까요?"):
                self.set_status("Auto Label 취소 (기존 후보 라벨 유지)", "warn")
                return
            overwrite = True

        self._run_async("Auto Label", bridge.run_auto_label, (path, self.dets, None, overwrite), self._apply)

    def _apply(self, result, _sec):
        if not result.ok:
            self.set_status(f"Auto Label 실패: {result.message}", "error")
            messagebox.showerror("Auto Label 실패", result.message)
            return

        cur = self.app.s.cur
        # 저장된 후보 TXT 를 다시 읽어서 화면에 올린다 (파일에 실제로 저장된 그대로 표시)
        res = read_label_file(result.label_path, cur.width, cur.height)
        boxes = [b for b in res.boxes if b.cls in ACTIVE_CLASS_IDS]

        mode = "replace"
        if cur.boxes:
            answer = messagebox.askyesnocancel(
                "화면에 적용",
                f"이 이미지에 기존 BBox {len(cur.boxes)}개가 있습니다.\n\n"
                "예: AI 후보로 바꾸기\n아니오: 기존 BBox 에 추가\n취소: 화면에는 적용 안 함 (후보 파일만 저장)")
            if answer is None:
                self.set_status(f"{result.message} · 화면 적용 안 함", "ok")
                return
            mode = "replace" if answer else "add"

        self.app.s.begin_edit()                         # Ctrl+Z 로 되돌릴 수 있게
        cur.boxes = boxes if mode == "replace" else cur.boxes + boxes
        self.app.selected = None
        self.hidden = True                              # 사람 라벨과 겹쳐 보이지 않게 AI 점선은 숨김
        self.hide_btn.set_text("결과 보기")
        self.hide_btn.set_active(True)
        self.app.after_edit()

        self.set_status(f"●  {result.message} · 화면에 {len(boxes)}개 표시 → 확인 후 [저장]", "ok")
        messagebox.showinfo("Auto Label 완료",
                            f"{result.message}\n위치: {result.label_path}\n\n"
                            f"후보 {len(boxes)}개를 화면에 올렸습니다.\n"
                            "확인 · 수정한 뒤 [저장] 하면 검수본으로 저장됩니다. (Ctrl+Z: 되돌리기)")
