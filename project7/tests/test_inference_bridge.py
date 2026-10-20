"""GUI 연결용 bridge 테스트 (GUI 없이 실행).

    python tests/test_inference_bridge.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from src.inference import bridge  # noqa: E402
from src.yolo.yolo_io import read_label_file  # noqa: E402


def _image(folder: Path, name="sample.jpg", size=(800, 600)) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (180, 60, 40)).save(path)
    return path


def test_detection_format() -> None:
    with tempfile.TemporaryDirectory() as d:
        img = _image(Path(d))
        dets = bridge.run_detection(img)
        assert dets, "더미 검출이 비어 있음"
        for x in dets:
            assert 0 <= x.conf <= 1 and x.x1 < x.x2 and x.y1 < x.y2
            assert 0 <= x.x1 and x.x2 <= 800 and 0 <= x.y1 and x.y2 <= 600
        assert dets == bridge.run_detection(img), "같은 이미지면 같은 결과여야 함"


def test_auto_label_save_and_overwrite() -> None:
    with tempfile.TemporaryDirectory() as d:
        img = _image(Path(d))
        out_dir = Path(d) / "candidate"
        dets = bridge.run_detection(img)
        r = bridge.run_auto_label(img, dets, out_dir=out_dir)
        assert r.ok and r.label_path.exists() and r.count == len(dets)
        assert len(read_label_file(r.label_path, 800, 600).boxes) == len(dets)

        again = bridge.run_auto_label(img, dets, out_dir=out_dir)              # 덮어쓰기 X
        assert not again.ok
        forced = bridge.run_auto_label(img, dets[:1], out_dir=out_dir, overwrite=True)
        assert forced.ok and forced.count == 1


def test_blocked_dirs() -> None:
    assert bridge.check_demo_allowed("/data/fr_test/images/a.jpg")
    assert bridge.check_demo_allowed("/data/bridge_holdout/a.jpg")
    assert bridge.check_demo_allowed("/data/raw/이물검출_학습데이터1/images/train/a.jpg") is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
