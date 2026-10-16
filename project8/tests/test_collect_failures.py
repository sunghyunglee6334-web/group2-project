import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collect", ROOT / "scripts" / "09_collect_failures.py")
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)


def write_val_csv(path):
    path.write_text(
        "image_name,split,source_dataset,scene_type\n"
        "abc.jpg,val,dataset2,normal_kimchi\n"
        "xyz.JPG,val,dataset1,\n",
        encoding="utf-8-sig",
    )
    return path


def test_load_val_info_basic(tmp_path):
    info = collect.load_val_info(write_val_csv(tmp_path / "val.csv"))
    assert info["abc"] == {"source_dataset": "dataset2", "scene_type": "normal_kimchi"}


def test_load_val_info_blank_and_ext(tmp_path):
    """확장자 대문자도 떼고, 빈 scene_type 은 빈 글자"""
    info = collect.load_val_info(write_val_csv(tmp_path / "val.csv"))
    assert info["xyz"]["scene_type"] == ""


def test_load_val_info_missing_column(tmp_path):
    p = tmp_path / "val.csv"
    p.write_text("image_name,split\nabc.jpg,val\n", encoding="utf-8-sig")
    with pytest.raises(ValueError):
        collect.load_val_info(p)

def make_case(tmp_path):
    """가짜 Val 3장: a = 맞힘, b = 놓침 1 + 헛박스 1, c = 정상 김치에 헛박스 1"""
    img_dir, gt_dir, pred_dir = tmp_path / "img", tmp_path / "gt", tmp_path / "pred"
    for d in (img_dir, gt_dir, pred_dir):
        d.mkdir()
    for stem in ("a", "b", "c"):
        (img_dir / f"{stem}.jpg").write_bytes(b"")
    (gt_dir / "a.txt").write_text("1 0.5 0.5 0.2 0.2\n")
    (pred_dir / "a.txt").write_text("1 0.5 0.5 0.2 0.2 0.9\n")
    (gt_dir / "b.txt").write_text("3 0.2 0.2 0.05 0.05\n")
    (pred_dir / "b.txt").write_text("0 0.8 0.8 0.1 0.1 0.6\n")
    (gt_dir / "c.txt").write_text("")
    (pred_dir / "c.txt").write_text("0 0.3 0.3 0.1 0.1 0.41\n")
    info = {"a": {"source_dataset": "dataset2", "scene_type": "kimchi_with_target"},
            "b": {"source_dataset": "dataset2", "scene_type": "kimchi_with_target"},
            "c": {"source_dataset": "dataset1", "scene_type": "normal_kimchi"}}
    images = sorted(img_dir.iterdir())
    return images, info, gt_dir, pred_dir


def test_collect_summary_sorted(tmp_path):
    images, info, gt_dir, pred_dir = make_case(tmp_path)
    summary, _ = collect.collect(images, info, gt_dir, pred_dir)
    assert [r["image"] for r in summary] == ["b.jpg", "c.jpg", "a.jpg"]
    assert summary[0]["n_fail"] == 2 and summary[-1]["TP"] == 1


def test_collect_fail_rows(tmp_path):
    images, info, gt_dir, pred_dir = make_case(tmp_path)
    _, fails = collect.collect(images, info, gt_dir, pred_dir)
    assert len(fails) == 3                                   # TP 는 빠짐
    fn = [r for r in fails if r["failure_type"] == "FN"][0]
    assert fn["ground_truth"] == "insect" and fn["prediction"] == "none"
    fp_c = [r for r in fails if r["image"] == "c.jpg"][0]
    assert fp_c["scene_type"] == "normal_kimchi" and fp_c["confidence"] == 0.41
    assert fp_c["suspected_cause"] == ""                     # 사람이 채울 칸


def test_collect_missing_info(tmp_path):
    """val.csv 에 없는 이미지도 멈추지 않고 빈칸으로"""
    images, _, gt_dir, pred_dir = make_case(tmp_path)
    summary, _ = collect.collect(images, {}, gt_dir, pred_dir)
    assert summary[0]["scene_type"] == ""

def test_main_type_tie_prefers_fn():
    row = {"FN": 1, "FP": 1, "CLASS": 0, "BBOX": 0}
    assert collect.main_type(row) == "FN"


def test_save_failure_images(tmp_path, monkeypatch):
    """실패 없는 이미지는 건너뛰고, 실패 이미지는 주된 유형 폴더로"""
    calls = []
    monkeypatch.setattr(collect, "visualize", lambda img, gt, out, names, pred_txt: calls.append(out))
    images, info, gt_dir, pred_dir = make_case(tmp_path)
    summary, _ = collect.collect(images, info, gt_dir, pred_dir)
    out = tmp_path / "out"
    n = collect.save_failure_images(summary, tmp_path / "img", gt_dir, pred_dir, out)
    assert n == 2
    assert sorted(p.relative_to(out).as_posix() for p in calls) == ["FN/b.jpg", "FP/c.jpg"]