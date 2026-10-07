"""라벨링 작업 세션 (GUI 와 분리된 핵심 로직).

GUI 는 화면만 담당하고, '데이터를 어떻게 바꾸고 저장하는가'는 전부 여기서 한다.
그래서 GUI 없이도 테스트할 수 있다 (tests/test_core.py).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from ..config import ACTIVE_CLASS_IDS, MIN_BOX_PX, Paths
from ..manifest import Manifest
from ..validation.validator import image_size
from ..yolo.dataset import ImageRecord, scan_images
from ..yolo.yolo_io import (Box, atomic_copy, atomic_write_text, boxes_to_text, format_line, pixel_to_yolo,
                            read_label_file)

FILTERS = {
    "전체": lambda row, me: True,
    "내 담당": lambda row, me: row["assignee"] == me,
    "내 담당-미완료": lambda row, me: row["assignee"] == me and row["status"] in ("PENDING", "WORKING"),
    "내 검수 대상": lambda row, me: row["reviewer"] == me and (
        row["status"] in ("EDITED", "REVIEW") or (row["status"] == "PASS" and row["pass_sample"] == "1")),
    "PENDING": lambda row, me: row["status"] == "PENDING",
    "EDITED": lambda row, me: row["status"] == "EDITED",
    "REVIEW": lambda row, me: row["status"] == "REVIEW",
    "PASS": lambda row, me: row["status"] == "PASS",
    "Pilot": lambda row, me: row["pilot"] == "1",
    "PASS 표본검수": lambda row, me: row["pass_sample"] == "1" and row["status"] == "PASS",
}


def canonical(boxes: list[Box], w: int, h: int) -> list[str]:
    """비교용 문자열 목록 (순서 무관)."""
    return sorted(format_line(*pixel_to_yolo(b, w, h)) for b in boxes)


@dataclass
class LoadedImage:
    rec: ImageRecord
    width: int
    height: int
    boxes: list[Box]
    raw_boxes: list[Box]                    # RAW 원본 (변경 여부 비교용)
    raw_text: str | None                    # RAW TXT 원문 (없으면 None)
    errors: list[str] = field(default_factory=list)
    from_work: bool = False
    raw_had_errors: bool = False
    undo_stack: list[list[Box]] = field(default_factory=list)
    loaded_snapshot: list[str] = field(default_factory=list)

    def changed_since_load(self) -> bool:
        return canonical(self.boxes, self.width, self.height) != self.loaded_snapshot

    def changed_vs_raw(self) -> bool:
        if self.raw_text is None or self.raw_had_errors:
            return True
        return canonical(self.boxes, self.width, self.height) != canonical(self.raw_boxes, self.width, self.height)


class LabelSession:
    def __init__(self, paths: Paths, worker: str = ""):
        paths.check_not_same()
        self.paths = paths
        self.worker = worker
        self.records: list[ImageRecord] = scan_images(paths.raw)
        if not self.records:
            raise SystemExit(f"RAW 폴더에 이미지가 없습니다: {paths.raw}")
        self.by_key = {r.rel_image: r for r in self.records}
        self.manifest = Manifest(paths.manifest)
        missing = [r for r in self.records if r.rel_image not in self.manifest.rows]
        if missing:
            from ..manifest_builder import add_records   # 순환 import 방지
            add_records(self.manifest, missing, paths)
            self.manifest.save()
        self.filter_name = "전체"
        self.view_keys: list[str] = [r.rel_image for r in self.records]
        self.index = 0
        self.cur: LoadedImage | None = None
        self.meta_dirty = False

    # ------------------------------------------------ 목록/필터
    def set_filter(self, name: str) -> int:
        fn = FILTERS[name]
        keys = [r.rel_image for r in self.records if fn(self.manifest.get(r.rel_image), self.worker)]
        self.filter_name = name
        self.view_keys = keys
        self.index = 0
        return len(keys)

    @property
    def total(self) -> int:
        return len(self.view_keys)

    @property
    def current_key(self) -> str | None:
        return self.view_keys[self.index] if self.view_keys else None

    # ------------------------------------------------ Load
    def load(self, index: int) -> LoadedImage:
        """index 이미지를 불러온다. 이전 이미지 상태는 완전히 버린다 (BBox 잔상 방지)."""
        self.index = max(0, min(index, self.total - 1))
        rec = self.by_key[self.view_keys[self.index]]
        w, h, _ = image_size(rec.raw_image(self.paths))
        raw_path = rec.raw_label(self.paths)
        raw_res = read_label_file(raw_path, w, h)
        raw_text = raw_path.read_text(encoding="utf-8-sig", errors="replace") if raw_path.exists() else None
        work_path = rec.work_label(self.paths)
        if work_path.exists():
            res = read_label_file(work_path, w, h)
            from_work = True
        else:
            res = raw_res
            from_work = False
        boxes = [copy.copy(b) for b in res.boxes]
        self.cur = LoadedImage(rec, w, h, boxes, raw_res.boxes, raw_text, list(res.errors), from_work,
                               raw_had_errors=bool(raw_res.errors) and raw_text is not None)
        self.cur.loaded_snapshot = canonical(boxes, w, h)
        self.meta_dirty = False
        return self.cur

    # ------------------------------------------------ 편집 (모두 원본 픽셀 좌표)
    def _push_undo(self) -> None:
        assert self.cur
        self.cur.undo_stack.append([copy.copy(b) for b in self.cur.boxes])
        del self.cur.undo_stack[:-50]

    def add_box(self, cls: int, x1: float, y1: float, x2: float, y2: float) -> Box | None:
        """새 BBox. 이미지 밖은 잘라내고, 너무 작으면 만들지 않는다."""
        assert self.cur
        if cls not in ACTIVE_CLASS_IDS:
            raise ValueError(f"Class {cls} 는 새 BBox 에 사용할 수 없습니다.")
        b = Box(cls, x1, y1, x2, y2).clamp(self.cur.width, self.cur.height)
        if b.w < MIN_BOX_PX or b.h < MIN_BOX_PX:
            return None
        self._push_undo()
        self.cur.boxes.append(b)
        return b

    def delete_box(self, idx: int) -> None:
        assert self.cur
        self._push_undo()
        del self.cur.boxes[idx]

    def set_box_class(self, idx: int, cls: int) -> None:
        assert self.cur
        if cls not in ACTIVE_CLASS_IDS:
            raise ValueError(f"Class {cls} 로 변경할 수 없습니다.")
        if self.cur.boxes[idx].cls == cls:
            return
        self._push_undo()
        self.cur.boxes[idx].cls = cls

    def move_box(self, idx: int, box: Box) -> None:
        """BBox 위치/크기 변경 (경계 Clamp)."""
        assert self.cur
        b = box.clamp(self.cur.width, self.cur.height)
        if b.w < MIN_BOX_PX or b.h < MIN_BOX_PX:
            return
        self._push_undo()
        self.cur.boxes[idx] = b

    def begin_edit(self) -> None:
        """드래그로 이동/크기조절을 시작할 때 1번만 Undo 지점을 만든다."""
        self._push_undo()

    def replace_box(self, idx: int, box: Box, push_undo: bool = True) -> bool:
        """BBox 를 새 좌표로 바꾼다 (이미지 경계 Clamp). 너무 작아지면 바꾸지 않는다."""
        assert self.cur
        b = box.clamp(self.cur.width, self.cur.height)
        if b.w < MIN_BOX_PX or b.h < MIN_BOX_PX:
            return False
        if push_undo:
            self._push_undo()
        self.cur.boxes[idx] = b
        return True

    def undo(self) -> bool:
        assert self.cur
        if not self.cur.undo_stack:
            return False
        self.cur.boxes = self.cur.undo_stack.pop()
        return True

    def find_box_at(self, x: float, y: float) -> int | None:
        """(x,y)를 포함하는 BBox 중 가장 작은 것 (겹친 작은 이물 선택이 쉽도록)."""
        assert self.cur
        hits = [(b.w * b.h, i) for i, b in enumerate(self.cur.boxes) if b.contains(x, y)]
        return min(hits)[1] if hits else None

    def is_dirty(self) -> bool:
        return bool(self.cur) and (self.cur.changed_since_load() or self.meta_dirty)

    # ------------------------------------------------ Save
    def save(self, status: str, scene_type: str = "", note: str = "", issue: str = "",
             reviewer: str = "") -> str:
        """WORK 에 TXT 저장 + Manifest 갱신. 실제 적용된 status 를 돌려준다.
        RAW 는 절대 쓰지 않는다."""
        assert self.cur
        cur, rec = self.cur, self.cur.rec
        work_path = rec.work_label(self.paths)
        if work_path.resolve().is_relative_to(self.paths.raw.resolve()):
            raise RuntimeError("WORK 저장 경로가 RAW 안에 있습니다. 저장 중단.")

        changed_vs_raw = cur.changed_vs_raw()
        # 상태 규칙
        if status in ("PENDING", "WORKING", ""):
            status = "EDITED" if changed_vs_raw else "PASS"
        if status == "PASS" and changed_vs_raw:
            status = "EDITED"           # 수정했으면 PASS 가 아니라 EDITED

        # TXT 저장: 라벨을 안 바꿨고 RAW 가 있으면 RAW 원문을 그대로 복사 (바이트 보존)
        if not changed_vs_raw:
            atomic_copy(rec.raw_label(self.paths), work_path)
        else:
            atomic_write_text(work_path, boxes_to_text(cur.boxes, cur.width, cur.height))

        row = self.manifest.get(rec.rel_image)
        fields = dict(status=status, final_bbox_count=len(cur.boxes), note=note, issue=issue)
        if scene_type:
            fields["scene_type"] = scene_type
        if not row["assignee"]:
            fields["assignee"] = self.worker
        if reviewer:
            fields["reviewer"] = reviewer
        if status == "REVIEWED":
            fields["reviewer"] = self.worker
        self.manifest.update(rec.rel_image, by=self.worker, **fields)
        self.manifest.save()

        # 저장 후 다시 읽어 '저장된 그대로' 상태로 맞춘다 (Save/Reload 일관성)
        cur.from_work = True
        cur.loaded_snapshot = canonical(cur.boxes, cur.width, cur.height)
        cur.errors = []
        self.meta_dirty = False
        return status

    def progress(self) -> dict[str, int]:
        return self.manifest.count_by("status")

    def index_of(self, rel_image: str) -> int | None:
        try:
            return self.view_keys.index(rel_image)
        except ValueError:
            return None

    def next_unfinished(self, start: int) -> int | None:
        """start 다음부터 PENDING/WORKING 인 첫 이미지 (현재 보기 안에서)."""
        n = self.total
        for k in range(1, n + 1):
            i = (start + k) % n
            if self.manifest.get(self.view_keys[i])["status"] in ("PENDING", "WORKING"):
                return i
        return None

    def class_counts(self) -> dict[int, int]:
        """현재 저장 기준(WORK, 없으면 RAW) 전체 Class 별 BBox 수. 이미지를 열지 않아 빠르다."""
        out: dict[int, int] = {}
        for rec in self.records:
            p = rec.effective_label(self.paths)
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                parts = line.split()
                if len(parts) == 5:
                    try:
                        c = int(float(parts[0]))
                    except ValueError:
                        continue
                    out[c] = out.get(c, 0) + 1
        return dict(sorted(out.items()))

