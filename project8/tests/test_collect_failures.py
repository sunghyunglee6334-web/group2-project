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