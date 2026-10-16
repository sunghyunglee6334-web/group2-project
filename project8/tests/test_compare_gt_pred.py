"""
tests/test_compare_gt_pred.py — scripts/compare_gt_pred.py 테스트

Weight 없이 돈다: YOLO를 가짜로 바꾸고, 가짜 이미지와 가짜 GT/Pred TXT로 시험.
project8 폴더에서 실행:
    pytest -q tests/test_compare_gt_pred.py
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]          # project8/
SCRIPT = ROOT / "scripts" / "compare_gt_pred.py"


# ---------------------------------------------------------------- 가짜 YOLO
class FakeYOLO:
    """predict 호출 때 runs/.../labels/이름.txt 를 써 줌. PRED 에 없는 이름은 파일을 안 만듦."""
    PRED = {}          # {stem: "cls x y w h conf\n..."}
    calls = []

    def __init__(self, weight):
        self.weight = weight

    def predict(self, source, project, name, **kw):
        FakeYOLO.calls.append((source, kw))
        stem = Path(source).stem
        if stem in FakeYOLO.PRED:
            out = Path(project) / name / "labels"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{stem}.txt").write_text(FakeYOLO.PRED[stem], encoding="utf-8")


@pytest.fixture
def cg(tmp_path, monkeypatch):
    """스크립트를 가짜 YOLO로 불러오고, 경로를 전부 tmp_path 아래로 바꿈"""
    FakeYOLO.PRED, FakeYOLO.calls = {}, []
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=FakeYOLO))
    spec = importlib.util.spec_from_file_location("compare_gt_pred", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.PROJECT_ROOT = tmp_path
    mod.WEIGHT = tmp_path / "models" / "baseline" / "baseline_best.pt"
    mod.IMAGE_DIR = tmp_path / "data" / "yolo" / "images" / "val"
    mod.LABEL_DIR = tmp_path / "data" / "yolo" / "labels" / "val"
    mod.PRED_RUN = tmp_path / "runs" / "pred_val"
    mod.OUT_DIR = tmp_path / "runs" / "compare_val"
    for d in (mod.WEIGHT.parent, mod.IMAGE_DIR, mod.LABEL_DIR):
        d.mkdir(parents=True)
    mod.WEIGHT.write_bytes(b"fake")                     # 존재만 확인하므로 빈 파일로 충분
    return mod


def make_images(mod, stems, gt="0 0.5 0.5 0.2 0.2\n"):
    """가짜 64x64 이미지 + GT TXT"""
    for s in stems:
        Image.new("RGB", (64, 64), (200, 200, 200)).save(mod.IMAGE_DIR / f"{s}.jpg")
        (mod.LABEL_DIR / f"{s}.txt").write_text(gt, encoding="utf-8")


def run(mod, monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["compare_gt_pred.py", *args])
    mod.main()


# ---------------------------------------------------------------- [1] predict
def test_predict_writes_txt_per_image(cg):
    make_images(cg, ["a", "b"])
    FakeYOLO.PRED = {"a": "0 0.5 0.5 0.2 0.2 0.91\n"}
    pred_dir = cg.predict(sorted(cg.IMAGE_DIR.iterdir()))

    assert pred_dir == cg.PRED_RUN / "labels"
    assert (pred_dir / "a.txt").is_file()
    assert not (pred_dir / "b.txt").exists()            # 예측 없으면 파일도 없음
    assert len(FakeYOLO.calls) == 2                     # 한 장씩 예측


def test_predict_options(cg):
    make_images(cg, ["a"])
    cg.predict([cg.IMAGE_DIR / "a.jpg"])
    _, kw = FakeYOLO.calls[0]
    assert kw["save_txt"] and kw["save_conf"]           # 확신도까지 저장해야 점선 옆에 씀
    assert kw["conf"] == cg.CONF
    assert kw["exist_ok"]                               # 다시 돌려도 pred_val2 안 생김


# ---------------------------------------------------------------- [2] main
def test_main_draws_all(cg, monkeypatch, capsys):
    make_images(cg, ["a", "b", "c"])
    FakeYOLO.PRED = {"a": "0 0.5 0.5 0.2 0.2 0.91\n", "b": "1 0.3 0.3 0.1 0.1 0.40\n"}
    run(cg, monkeypatch)

    out = sorted(p.name for p in cg.OUT_DIR.glob("*.jpg"))
    assert out == ["a.jpg", "b.jpg", "c.jpg"]           # 예측 없는 c도 GT만 그려서 저장
    assert "예측 없음 1장" in capsys.readouterr().out


def test_main_n_limits(cg, monkeypatch):
    make_images(cg, ["a", "b", "c"])
    run(cg, monkeypatch, "--n", "2")
    assert sorted(p.name for p in cg.OUT_DIR.glob("*.jpg")) == ["a.jpg", "b.jpg"]
    assert len(FakeYOLO.calls) == 2


def test_main_skips_non_images(cg, monkeypatch):
    make_images(cg, ["a"])
    (cg.IMAGE_DIR / "readme.txt").write_text("x", encoding="utf-8")
    run(cg, monkeypatch)
    assert [Path(s).name for s, _ in FakeYOLO.calls] == ["a.jpg"]


def test_main_passes_pred_txt(cg, monkeypatch):
    """visualize 에 GT/Pred 경로가 이름대로 넘어가는지"""
    make_images(cg, ["a"])
    got = []
    monkeypatch.setattr(cg, "visualize", lambda img, gt, out, names, pred_txt=None:
                        got.append((img.name, gt.name, out.name, pred_txt.name)))
    run(cg, monkeypatch)
    assert got == [("a.jpg", "a.txt", "a.jpg", "a.txt")]


@pytest.mark.parametrize("missing", ["WEIGHT", "IMAGE_DIR", "LABEL_DIR"])
def test_main_missing_input(cg, monkeypatch, missing):
    path = getattr(cg, missing)
    if path.is_dir():
        path.rmdir()
    else:
        path.unlink()
    with pytest.raises(SystemExit, match="없습니다"):
        run(cg, monkeypatch)
