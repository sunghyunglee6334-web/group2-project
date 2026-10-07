"""프로그램 안에 내장한 두벌식 한글 입력기.

왜 필요한가?
  WSL(WSLg)에서 띄운 Tkinter 창에는 Windows 한글 IME 가 전달되지 않는다.
  그래서 이슈/메모 칸에 한글을 칠 수 없었다.
  이 모듈은 키보드 영문 키를 직접 받아 한글 음절로 조합해 넣는다. (IME 설치 불필요)

사용법
  ime = HangulIME(root)
  ime.attach(entry)            # tk.Entry / ttk.Entry / ttk.Combobox / tk.Text 모두 가능
  한/영 전환: Shift+Space, 한/영 키, 오른쪽 Alt, 또는 메모 옆 [영문/한글] 버튼

Windows 에서 직접 실행하는 등 원래 IME 가 동작하는 환경이면
[A] 상태로 두고 원래 IME 로 입력해도 된다 (이 입력기는 영문 키만 가로챈다).
"""
from __future__ import annotations

import tkinter as tk

# ---------------------------------------------------------------- 자모 표
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ",
        "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]

# 두벌식 자판 (Shift 를 누르면 쌍자음 / ㅒ ㅖ)
KEYMAP = {
    "q": "ㅂ", "w": "ㅈ", "e": "ㄷ", "r": "ㄱ", "t": "ㅅ", "y": "ㅛ", "u": "ㅕ", "i": "ㅑ", "o": "ㅐ", "p": "ㅔ",
    "a": "ㅁ", "s": "ㄴ", "d": "ㅇ", "f": "ㄹ", "g": "ㅎ", "h": "ㅗ", "j": "ㅓ", "k": "ㅏ", "l": "ㅣ",
    "z": "ㅋ", "x": "ㅌ", "c": "ㅊ", "v": "ㅍ", "b": "ㅠ", "n": "ㅜ", "m": "ㅡ",
    "Q": "ㅃ", "W": "ㅉ", "E": "ㄸ", "R": "ㄲ", "T": "ㅆ", "O": "ㅒ", "P": "ㅖ",
}

VOWEL_PAIRS = {("ㅗ", "ㅏ"): "ㅘ", ("ㅗ", "ㅐ"): "ㅙ", ("ㅗ", "ㅣ"): "ㅚ", ("ㅜ", "ㅓ"): "ㅝ",
               ("ㅜ", "ㅔ"): "ㅞ", ("ㅜ", "ㅣ"): "ㅟ", ("ㅡ", "ㅣ"): "ㅢ"}
JONG_PAIRS = {("ㄱ", "ㅅ"): "ㄳ", ("ㄴ", "ㅈ"): "ㄵ", ("ㄴ", "ㅎ"): "ㄶ", ("ㄹ", "ㄱ"): "ㄺ", ("ㄹ", "ㅁ"): "ㄻ",
              ("ㄹ", "ㅂ"): "ㄼ", ("ㄹ", "ㅅ"): "ㄽ", ("ㄹ", "ㅌ"): "ㄾ", ("ㄹ", "ㅍ"): "ㄿ", ("ㄹ", "ㅎ"): "ㅀ",
              ("ㅂ", "ㅅ"): "ㅄ"}
JONG_SPLIT = {v: k for k, v in JONG_PAIRS.items()}


def is_vowel(j: str) -> bool:
    return j in JUNG


def jamo_for_key(char: str, shift: bool) -> str | None:
    """눌린 글자 -> 자모. Caps Lock 으로 대문자가 들어오면(Shift 없이) 소문자로 본다."""
    if not char or len(char) != 1 or not char.isascii() or not char.isalpha():
        return None
    if char.isupper() and not shift:
        char = char.lower()
    return KEYMAP.get(char) or KEYMAP.get(char.lower())


class HangulComposer:
    """한 글자(음절)를 조합하는 상태 기계. Tk 와 무관해서 단독으로 테스트할 수 있다."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.cho: str | None = None
        self.jung: str | None = None
        self.jong: str | None = None
        self.history: list[tuple] = []      # 백스페이스용: 자모 하나 넣을 때마다의 상태

    @property
    def composing(self) -> bool:
        return bool(self.cho or self.jung)

    def text(self) -> str:
        """지금 조합 중인 글자."""
        if self.cho and self.jung:
            code = 0xAC00 + (CHO.index(self.cho) * 21 + JUNG.index(self.jung)) * 28 + JONG.index(self.jong or "")
            return chr(code)
        return self.cho or self.jung or ""

    def _save(self) -> None:
        self.history.append((self.cho, self.jung, self.jong))

    def _start(self, cho=None, jung=None) -> None:
        self.reset()
        if cho:
            self.cho = cho
            self._save()
        if jung:
            self.jung = jung
            self._save()

    def feed(self, j: str) -> str:
        """자모 하나를 넣는다. 확정되어 앞으로 빠져나간 글자를 돌려준다 (없으면 '')."""
        if is_vowel(j):
            return self._feed_vowel(j)
        return self._feed_consonant(j)

    def _feed_consonant(self, c: str) -> str:
        if self.cho and self.jung:
            if self.jong is None:
                if c in JONG:                       # ㄸ ㅃ ㅉ 은 받침이 될 수 없다
                    self.jong = c
                    self._save()
                    return ""
            elif (self.jong, c) in JONG_PAIRS:
                self.jong = JONG_PAIRS[(self.jong, c)]
                self._save()
                return ""
        if not self.composing:
            self._start(cho=c)
            return ""
        done = self.text()
        self._start(cho=c)
        return done

    def _feed_vowel(self, v: str) -> str:
        if self.cho and self.jung and self.jong:
            # 받침이 다음 글자의 첫소리로 넘어간다: 갃 + ㅏ -> 각 + 사
            if self.jong in JONG_SPLIT:
                keep, move = JONG_SPLIT[self.jong]
            else:
                keep, move = None, self.jong
            self.jong = keep
            done = self.text()
            self._start(cho=move, jung=v)
            return done
        if self.jung and (self.jung, v) in VOWEL_PAIRS:
            self.jung = VOWEL_PAIRS[(self.jung, v)]
            self._save()
            return ""
        if self.cho and not self.jung:
            self.jung = v
            self._save()
            return ""
        if not self.composing:
            self._start(jung=v)
            return ""
        done = self.text()
        self._start(jung=v)
        return done

    def backspace(self) -> bool:
        """조합 중이면 자모 하나를 지운다. 조합 중이 아니면 False (원래 백스페이스가 동작)."""
        if not self.history:
            return False
        self.history.pop()
        if self.history:
            self.cho, self.jung, self.jong = self.history[-1]
        else:
            self.cho = self.jung = self.jong = None
        return True

    def flush(self) -> str:
        done = self.text()
        self.reset()
        return done


# ---------------------------------------------------------------- Tk 위젯 연결
class _Target:
    """Entry 계열과 Text 의 인덱스 차이를 감춘다."""

    def __init__(self, widget):
        self.w = widget
        self.is_text = isinstance(widget, tk.Text)

    def insert_index(self):
        return self.w.index("insert")

    def offset(self, start, n):
        return f"{start}+{n}c" if self.is_text else int(start) + n

    def replace(self, start, old_len, new):
        w = self.w
        if old_len:
            w.delete(start, self.offset(start, old_len))
        if new:
            w.insert(start, new)
        end = self.offset(start, len(new))
        if self.is_text:
            w.mark_set("insert", end)
            w.see("insert")
        else:
            w.icursor(end)
            self._see_insert()
        return end

    def _see_insert(self):
        """긴 글을 칠 때 커서가 칸 밖으로 나가지 않게 (Tk 기본 입력과 같은 동작)."""
        w = self.w
        for cmd in (("::tk::EntrySeeInsert", str(w)), ("ttk::entry::See", str(w), "insert")):
            try:
                w.tk.call(*cmd)
                return
            except tk.TclError:
                continue

    def delete_selection(self):
        w = self.w
        try:
            if self.is_text:
                if w.tag_ranges("sel"):
                    w.delete("sel.first", "sel.last")
            elif w.selection_present():
                w.delete("sel.first", "sel.last")
        except tk.TclError:
            pass


class HangulIME:
    """여러 입력칸이 같은 한/영 상태를 공유한다."""

    TOGGLE_KEYS = ("<Shift-space>", "<KeyPress-Hangul>", "<KeyPress-Alt_R>")

    def __init__(self, root, korean: bool = False):
        self.root = root
        self.korean = korean
        self.listeners = []
        self.comp = HangulComposer()
        self.target: _Target | None = None
        self.start = None
        self.length = 0

    # ---- 상태
    def on_change(self, func) -> None:
        """한/영이 바뀔 때 부를 함수 (버튼 글자 바꾸기 등)."""
        self.listeners.append(func)
        func(self.korean)

    def toggle(self, _event=None):
        self.commit()
        self.korean = not self.korean
        for func in self.listeners:
            func(self.korean)
        return "break"

    def commit(self, _event=None) -> None:
        """조합 중인 글자를 그대로 확정한다 (글자는 이미 칸에 들어가 있다)."""
        self.comp.reset()
        self.target = None
        self.start = None
        self.length = 0

    # ---- 연결
    def attach(self, widget) -> None:
        widget.bind("<KeyPress>", self._on_key, add="+")
        widget.bind("<BackSpace>", self._on_backspace)
        for seq in self.TOGGLE_KEYS:
            try:
                widget.bind(seq, self.toggle)
            except tk.TclError:         # 그 OS 의 Tk 가 모르는 키 이름이면 건너뜀
                pass
        for seq in ("<ButtonPress>", "<FocusOut>", "<FocusIn>"):
            widget.bind(seq, self.commit, add="+")

    # ---- 키 처리
    def _on_key(self, event):
        if event.state & 0x4:                       # Ctrl 조합(복사/붙여넣기 등)은 그대로
            self.commit()
            return None
        if not self.korean:
            return None
        jamo = jamo_for_key(event.char, shift=bool(event.state & 0x1))
        if jamo is None:
            # 숫자, 공백, 기호, 방향키 ... -> 조합을 끝내고 원래 동작
            if event.keysym not in ("Shift_L", "Shift_R", "Caps_Lock"):
                self.commit()
            return None

        target = self.target if self.target and self.target.w is event.widget else None
        if target is None or not self.comp.composing:
            self.commit()
            target = _Target(event.widget)
            target.delete_selection()
            self.target = target
            self.start = target.insert_index()
            self.length = 0

        done = self.comp.feed(jamo)
        self._show(done)
        return "break"

    def _on_backspace(self, event):
        if self.target is None or self.target.w is not event.widget or not self.comp.composing:
            self.commit()
            return None
        self.comp.backspace()
        self._show("")
        if not self.comp.composing:
            self.commit()
        return "break"

    def _show(self, done: str) -> None:
        now = self.comp.text()
        t = self.target
        t.replace(self.start, self.length, done + now)
        self.start = t.offset(self.start, len(done))
        if t.is_text:
            self.start = t.w.index(self.start)
        self.length = len(now)
        # 값이 바뀐 것을 알린다 (Text 는 <<Modified>>, Entry 는 textvariable 이 알아서)
