"""핵심 로직 자동 테스트 (GUI 없이 실행).

    python tests/test_core.py
가짜 데이터를 임시 폴더에 만들고, 실제 팀 작업 흐름 전체를 흉내 낸다:
manifest -> 배분 -> 2명이 각자 작업 -> 병합 -> 교차검수 -> PASS 표본 -> FINAL -> Handoff
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import Paths  # noqa: E402
from src.manifest import Manifest  # noqa: E402
from src.bbox.session import LabelSession  # noqa: E402
from src.validation.validator import critical_count, validate  # noqa: E402
from src.bbox.view import ViewTransform  # noqa: E402
from src.yolo.yolo_io import Box, boxes_to_text, parse_label_text  # noqa: E402

PY = sys.executable


def run(*args: str, ok=(0,)) -> str:
    r = subprocess.run([PY, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode in ok, f"{args} 실패({r.returncode}):\n{r.stdout}\n{r.stderr}"
    return r.stdout


def test_yolo_roundtrip() -> None:
    text = "0 0.500000 0.500000 0.100000 0.200000\n6 0.010000 0.990000 0.020000 0.020000\n"
    res = parse_label_text(text, 3840, 2160)
    assert not res.errors and len(res.boxes) == 2
    assert boxes_to_text(res.boxes, 3840, 2160) == text
    bad = parse_label_text("1 0.5 0.5\nx 1 1 1 1\n1.5 0.1 0.1 0.1 0.1\n", 100, 100)
    assert len(bad.errors) == 3


def test_view_zoom_keeps_point() -> None:
    v = ViewTransform()
    v.fit(3840, 2160, 1200, 800)
    before = v.to_image(400, 300)
    v.zoom_at(3.0, 400, 300)
    after = v.to_image(400, 300)
    assert abs(before[0] - after[0]) < 1e-9 and abs(before[1] - after[1]) < 1e-9
    v.pan(50, 20)
    x, y = v.to_canvas(*v.to_image(123, 456))
    assert abs(x - 123) < 1e-9 and abs(y - 456) < 1e-9


def worker_session(raw: Path, work: Path, who: str) -> None:
    """담당 이미지를 처리하는 작업자 흉내."""
    s = LabelSession(Paths(raw, work), who)
    s.set_filter("내 담당")
    for i in range(s.total):
        cur = s.load(i)
        bad = [j for j, b in enumerate(cur.boxes) if b.cls not in (0, 1, 2, 3, 5, 6)]
        if any(b.cls == 4 for b in cur.boxes):
            s.save("REVIEW", note="Class 4 발견 - 2인 확인 필요")
            continue
        for j in reversed(bad):
            s.delete_box(j)
        # 경계 밖/중복 BBox 정리: 이미지 밖으로 나간 박스는 다시 그리기
        for j in reversed(range(len(cur.boxes))):
            b = cur.boxes[j]
            if b.x1 < 0 or b.y1 < 0 or b.x2 > cur.width or b.y2 > cur.height:
                s.delete_box(j)
        seen = []
        for j in reversed(range(len(cur.boxes))):
            key = tuple(round(v, 1) for v in (cur.boxes[j].x1, cur.boxes[j].y1, cur.boxes[j].cls))
            if key in seen:
                s.delete_box(j)
            seen.append(key)
        scene = "normal_kimchi" if not cur.boxes else "kimchi_with_target"
        s.save("PASS", scene_type=scene, note="")


def test_full_workflow() -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        raw, work = tmp / "raw", tmp / "work"
        run("scripts/make_dummy_data.py", "--out", str(raw), "--n1", "10", "--n2", "8", "--n2v", "6")
        run("scripts/01_build_manifest.py", "--raw", str(raw), "--work", str(work))
        run("scripts/00_raw_snapshot.py", "--raw", str(raw), "--work", str(work))
        run("scripts/03_assign.py", "--workers", "A", "B", "--pilot", "6", "--work", str(work))
        # 짝 없는 TXT 는 WORK 에서 해결할 수 없다 -> 실제로는 담당자에게 보고. 테스트에서는 제거.
        for p in raw.rglob("orphan_without_image.txt"):
            p.unlink()
        run("scripts/00_raw_snapshot.py", "--raw", str(raw), "--work", str(work))   # 기준 재생성
        # 각자 자기 PC 사본에서 작업
        wa, wb = tmp / "work_A", tmp / "work_B"
        shutil.copytree(work, wa)
        shutil.copytree(work, wb)
        raw_before = {p: p.read_bytes() for p in raw.rglob("*") if p.is_file()}
        worker_session(raw, wa, "A")
        worker_session(raw, wb, "B")
        merged = tmp / "merged"
        out = run("scripts/04_merge.py", "--inputs", str(wa), str(wb), "--out", str(merged))
        assert "동시 수정 의심 0건" in out, out
        m = Manifest(merged / "manifest.csv")
        assert m.count_by("status").get("PENDING", 0) == 0, m.count_by("status")

        # 교차검수: 각자 상대의 EDITED/REVIEW 를 확인
        for who in ("A", "B"):
            s = LabelSession(Paths(raw, merged), who)
            s.set_filter("내 검수 대상")
            for i in range(s.total):
                cur = s.load(i)
                if any(b.cls == 4 for b in cur.boxes):    # 2인 확인 결과: 실제 이물 = 플라스틱(1)로 판정
                    for j, b in enumerate(cur.boxes):
                        if b.cls == 4:
                            s.set_box_class(j, 1)
                s.save("REVIEWED", note="교차검수 확인")
        run("scripts/06_pass_sample.py", "--ratio", "0.3", "--raw", str(raw), "--work", str(merged))
        for who in ("A", "B"):
            s = LabelSession(Paths(raw, merged), who)
            s.set_filter("내 검수 대상")
            for i in range(s.total):
                s.load(i)
                s.save("REVIEWED", note="PASS 표본검수 이상 없음")
        # TXT 없는 이미지: WORK 에 저장되었으므로 Pair 오류 해소
        issues = validate(Paths(raw, merged))
        assert critical_count(issues) == 0, [(i.code, i.rel_path, i.message) for i in issues if i.severity == "CRITICAL"]
        final = tmp / "final"
        run("scripts/07_build_final.py", "--raw", str(raw), "--work", str(merged), "--final", str(final))
        assert (final / "manifest_final.csv").exists()
        n_img = len([p for p in final.rglob("*.jpg")])
        n_txt = len([p for p in final.rglob("*.txt")])
        assert n_img == n_txt == 24, (n_img, n_txt)
        run("scripts/05_qa_summary.py", "--raw", str(raw), "--work", str(merged), "--out", str(tmp / "qa_summary.md"))
        run("scripts/08_handoff.py", "--raw", str(raw), "--work", str(merged), "--final", str(final),
            "--out", str(tmp / "subject08_handoff.md"))
        assert (final / "images").is_dir() and (final / "labels").is_dir()
        assert len(list((final / "images").iterdir())) == len(list((final / "labels").iterdir())) == 24
        run("scripts/10_export_manifest.py", "--raw", str(raw), "--work", str(merged),
            "--out", str(tmp / "dataset_manifest.csv"))
        assert (tmp / "dataset_manifest.csv").exists()
        # RAW 는 하나도 바뀌지 않아야 한다
        for p, b in raw_before.items():
            assert p.read_bytes() == b, f"RAW 변경: {p}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_session_rules() -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        raw = tmp / "raw"
        run("scripts/make_dummy_data.py", "--out", str(raw), "--n1", "6", "--n2", "6", "--n2v", "6")
        s = LabelSession(Paths(raw, tmp / "work"), "T")
        cur = s.load(0)
        n = len(cur.boxes)
        assert s.add_box(2, 10, 10, 11, 11) is None            # 너무 작은 실수 드래그
        b = s.add_box(2, -50, -50, 200, 150)                    # 이미지 밖 -> Clamp
        assert b and b.x1 == 0 and b.y1 == 0
        try:
            s.add_box(4, 0, 0, 100, 100)
            raise AssertionError("Class 4 새 BBox 가 허용됨")
        except ValueError:
            pass
        assert s.is_dirty()
        s.undo()
        assert len(s.cur.boxes) == n and not s.is_dirty()
        # 다음 이미지로 가면 이전 BBox 가 남지 않는다
        s.add_box(2, 100, 100, 300, 300)
        nxt = s.load(1)
        assert s.cur is nxt and not nxt.undo_stack
        # 저장 상태 규칙
        s.load(2)
        s.add_box(1, 100, 100, 400, 400)
        assert s.save("PASS") == "EDITED"
        s.load(3)
        st = s.save("PENDING")
        assert st in ("PASS", "EDITED")
        assert s.cur.rec.work_label(s.paths).exists()
        assert not Box(0, 0, 0, 1, 1).contains(2, 2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    tests = [test_yolo_roundtrip, test_view_zoom_keeps_point, test_session_rules, test_full_workflow]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n모든 테스트 통과 ({len(tests)}개)")
