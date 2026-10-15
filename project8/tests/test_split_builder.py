"""
tests/test_split_builder.py — src/split_builder.py 테스트

project8 폴더에서 실행:
    pytest -q tests/test_split_builder.py
"""
import csv
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]          # project8/
sys.path.insert(0, str(ROOT))

from src import split_builder as sb  # noqa: E402
from src.split_builder import CLASS_NAMES, DEFAULT_POLICY, SPLITS, SplitError  # noqa: E402

MANIFESTS = ROOT / "manifests"
SIZES = {"train": 600, "val": 75, "test": 75, "bridge_holdout": 150}


# ---------------------------------------------------------------- 가짜 manifest
COLS = ["relative_path", "image_name", "label_name", "label_relative_path", "source_dataset",
        "original_split", "scene_type", "final_bbox_count", "issue", "note"]


def make_manifest(root: Path, times, labels=None, note=None):
    """times: 'YYMMDD_HHMMSSffffff' 목록. labels: {이름: [(cls, x, y, w, h), ...]}"""
    labels = labels or {}
    (root / "labels").mkdir(parents=True, exist_ok=True)
    rows = []
    for t in times:
        boxes = labels.get(t, [])
        if t in labels:
            (root / "labels" / f"{t}.txt").write_text(
                "".join(f"{c} {x} {y} {w} {h}\n" for c, x, y, w, h in boxes), encoding="utf-8")
        rows.append({"relative_path": f"images/{t}.jpg", "image_name": f"{t}.jpg",
                     "label_name": f"{t}.txt", "label_relative_path": f"labels/{t}.txt",
                     "source_dataset": "이물검출_학습데이터1", "original_split": "train",
                     "scene_type": "kimchi_with_target", "final_bbox_count": len(boxes),
                     "issue": "", "note": (note or {}).get(t, "")})
    man = root / "manifest_final.csv"
    with open(man, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(rows)
    return man


def load(tmp_path, times, **kw):
    man = make_manifest(tmp_path, times, **kw)
    return sb.load(man, tmp_path, sb._merge(DEFAULT_POLICY, {}), expected_total=len(times))


# ---------------------------------------------------------------- 상수
def test_split_names():
    assert SPLITS == ["train", "val", "test", "bridge_holdout"]


def test_default_sizes_make_600_75_75_150():
    sizes = DEFAULT_POLICY["sizes"]
    assert {**sizes, "train": 900 - sum(sizes.values())} == SIZES


def test_class_names_are_real_names():
    assert sorted(CLASS_NAMES) == list(range(7))
    assert not any(v.startswith("class_") for v in CLASS_NAMES.values())
    assert DEFAULT_POLICY["export"]["class_names"] == CLASS_NAMES


# ---------------------------------------------------------------- 준비 단계
def test_capture_time_from_file_name():
    assert sb._capture_time("250410_144403911987.jpg") == pd.Timestamp("2025-04-10 14:44:03.911987")
    with pytest.raises(SplitError):
        sb._capture_time("no_time.jpg")


@pytest.mark.parametrize("k, b", [(0, "0"), (1, "1-2"), (2, "1-2"), (3, "3-4"), (4, "3-4"), (5, "5-6"), (6, "5-6")])
def test_diversity_bin(k, b):
    assert sb.diversity_bin(k) == b


def test_load_reads_labels_and_flags(tmp_path):
    times = ["250410_090000000000", "250410_090010000000"]
    df = load(tmp_path, times, labels={times[0]: [(3, .5, .5, .1, .1), (6, .2, .2, .1, .1)], times[1]: []},
              note={times[1]: "REVIEW 필요"})
    assert df.loc[0, "_classes"] == ["3", "6"]
    assert list(df["is_background"]) == [False, True]
    assert list(df["label_ambiguous"]) == [False, True]


def test_load_checks_row_count(tmp_path):
    man = make_manifest(tmp_path, ["250410_090000000000"])
    with pytest.raises(SplitError):
        sb.load(man, tmp_path, sb._merge(DEFAULT_POLICY, {}), expected_total=900)


# ---------------------------------------------------------------- [1단계] 묶음
def test_new_group_after_5_minute_gap(tmp_path):
    times = ["250410_090000000000", "250410_090100000000",   # 1분 간격 → 같은 묶음
             "250410_091000000000", "250410_091030000000"]   # 9분 쉼 → 새 묶음
    df = load(tmp_path, times)
    df = sb.step1_make_groups(df, 300, sb._merge(DEFAULT_POLICY, {"scene_pair": {"enabled": False}}), [], [])
    assert list(df["time_group"]) == ["T00", "T00", "T01", "T01"]


# ---------------------------------------------------------------- [6-4] dataset.yaml
def test_write_dataset_yaml_relative_paths(tmp_path):
    y = sb.write_dataset_yaml(tmp_path, DEFAULT_POLICY)
    d = yaml.safe_load(y.read_text(encoding="utf-8"))
    assert "path" not in d
    assert d["train"] == "../data/yolo/images/train"
    assert d["val"] == "../data/yolo/images/val"
    assert d["test"] == "../data/yolo/images/test"
    assert d["names"] == CLASS_NAMES


def test_saved_dataset_yaml():
    d = yaml.safe_load((ROOT / "configs" / "dataset.yaml").read_text(encoding="utf-8"))
    assert "path" not in d
    assert d["train"].startswith("../data/yolo/images/")
    assert d["names"] == CLASS_NAMES


# ---------------------------------------------------------------- 저장된 Split 결과 (산출물 1)
@pytest.fixture(scope="module")
def saved():
    p = MANIFESTS / "split_manifest.csv"
    if not p.exists():
        pytest.skip("manifests/split_manifest.csv 없음 — scripts/03_build_split.py 먼저 실행")
    return pd.read_csv(p, encoding="utf-8-sig")


def test_saved_split_sizes(saved):
    assert saved["split"].value_counts().to_dict() == SIZES


def test_saved_split_files_match(saved):
    for s in SPLITS:
        part = pd.read_csv(MANIFESTS / f"{s}.csv", encoding="utf-8-sig")
        assert set(part["image_name"]) == set(saved.loc[saved["split"] == s, "image_name"])


def test_saved_no_group_leakage(saved):
    assert (saved.groupby("group_id")["split"].nunique() == 1).all()
    whole = saved[~saved["same_bundle_split"]]
    assert (whole.groupby("time_group")["split"].nunique() == 1).all()


def test_saved_uses_latest_ledger(saved):
    """main 최신 장부(manifest_final.csv): scene_type none 2장"""
    assert (saved["scene_type"] == "none").sum() == 2
