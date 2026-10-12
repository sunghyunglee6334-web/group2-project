"""QA 통계 계산 (QA Summary / Handoff 공통)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..config import CLASS_NAMES, Paths
from ..manifest import Manifest
from ..yolo.dataset import ImageRecord
from ..yolo.final_layout import final_label_path, final_stems
from ..yolo.yolo_io import Box, iou, read_label_file
from .validator import image_size

MATCH_IOU = 0.5     # 같은 객체로 볼 IoU
MOVED_IOU = 0.98    # 이보다 낮으면 위치/크기 수정으로 본다


def diff_boxes(raw: list[Box], final: list[Box]) -> dict[str, int]:
    """RAW 와 최종 BBox 비교 -> 추가/삭제/Class변경/위치수정/동일 개수."""
    pairs = sorted(((iou(r, f), i, j) for i, r in enumerate(raw) for j, f in enumerate(final)), reverse=True)
    used_r, used_f = set(), set()
    out = Counter(same=0, moved=0, class_changed=0, added=0, deleted=0)
    for v, i, j in pairs:
        if v < MATCH_IOU or i in used_r or j in used_f:
            continue
        used_r.add(i); used_f.add(j)
        if raw[i].cls != final[j].cls:
            out["class_changed"] += 1
        elif v < MOVED_IOU:
            out["moved"] += 1
        else:
            out["same"] += 1
    out["deleted"] = len(raw) - len(used_r)
    out["added"] = len(final) - len(used_f)
    return dict(out)


def collect(paths: Paths, records: list[ImageRecord], manifest: Manifest,
            label_root: Path | None = None) -> dict:
    """label_root(FINAL 폴더)가 주어지면 그 labels/ 를, 아니면 WORK(없으면 RAW)를 최종으로 본다."""
    stems = final_stems(records) if label_root else {}
    st = dict(images=len(records), txt_final=0, empty_final=0,
              class_raw=Counter(), class_final=Counter(), diff=Counter(),
              by_source=Counter(), by_split=Counter(), by_source_split=Counter(),
              by_scene=Counter(), by_status=Counter(), scene_class=Counter())
    for rec in records:
        row = manifest.rows.get(rec.rel_image, {})
        w, h, _ = image_size(rec.raw_image(paths))
        raw = read_label_file(rec.raw_label(paths), w, h).boxes
        lp = final_label_path(label_root, stems[rec.rel_image]) if label_root else rec.effective_label(paths)
        if lp.exists():
            st["txt_final"] += 1
        fin = read_label_file(lp, w, h).boxes
        if not fin:
            st["empty_final"] += 1
        st["class_raw"].update(b.cls for b in raw)
        st["class_final"].update(b.cls for b in fin)
        st["diff"].update(diff_boxes(raw, fin))
        st["by_source"][rec.source_dataset] += 1
        st["by_split"][rec.original_split] += 1
        st["by_source_split"][f"{rec.source_dataset}/{rec.original_split}"] += 1
        scene = row.get("scene_type") or "(미기록)"
        st["by_scene"][scene] += 1
        st["by_status"][row.get("status", "?")] += 1
        for b in fin:
            st["scene_class"][(scene, b.cls)] += 1
    rows = manifest.rows.values()
    st["pilot"] = sum(1 for r in rows if r["pilot"] == "1")
    st["pass_sample"] = sum(1 for r in rows if r["pass_sample"] == "1")
    st["pass_sample_done"] = sum(1 for r in rows if r["pass_sample"] == "1" and r["status"] in ("REVIEWED", "FINAL"))
    st["by_assignee"] = Counter(r["assignee"] or "(미배정)" for r in rows)
    st["reviewed"] = sum(1 for r in rows if r["reviewer"] and r["status"] in ("REVIEWED", "FINAL"))
    return st


def class_table(st: dict) -> list[str]:
    lines = ["| Class | 이름 | RAW BBox | 최종 BBox | 변화 |", "|---:|---|---:|---:|---:|"]
    for cid, name in CLASS_NAMES.items():
        r, f = st["class_raw"][cid], st["class_final"][cid]
        lines.append(f"| {cid} | {name} | {r} | {f} | {f - r:+d} |")
    others = set(st["class_raw"]) | set(st["class_final"])
    for cid in sorted(c for c in others if c not in CLASS_NAMES):
        lines.append(f"| {cid} | (범위 밖) | {st['class_raw'][cid]} | {st['class_final'][cid]} | |")
    lines.append(f"| 합계 | | {sum(st['class_raw'].values())} | {sum(st['class_final'].values())} | |")
    return lines


def counter_table(title: str, c: Counter) -> list[str]:
    lines = [f"| {title} | 수 |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(c.items())]
    return lines
