"""
tests/test_split_builder.py — src/split_builder.py, scripts/03_build_split.py 테스트

project8 폴더에서 실행:
    pytest -q tests/test_split_builder.py
"""
import csv
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]          # project8/
sys.path.insert(0, str(ROOT))

from src import split_builder as sb  # noqa: E402
from src.split_builder import ROLES, SPLITS  # noqa: E402

SCRIPT = ROOT / "scripts" / "03_build_split.py"
SCENES = ["kimchi_obj", "obj", "kimchi_only"]
NAMES = ["hair", "vinyl", "insect", "stone"]


# ---------------------------------------------------------------- 가짜 데이터
def make_dataset(root: Path, n=900, seed=0, rare_cell=False):
    """캡쳐그룹(1~8장) 단위의 가짜 데이터. 이물 없는 이미지 중 절반은 라벨 파일 자체가 없음."""
    rng = random.Random(seed)
    img_dir, lbl_dir = root / "images", root / "labels"
    img_dir.mkdir(parents=True)
    lbl_dir.mkdir(parents=True)
    rows, i, g = [], 0, 0
    while i < n:
        scene = rng.choice(SCENES)
        k = 0 if scene == "kimchi_only" else rng.choice([1, 1, 1, 2, 3])
        for _ in range(rng.randint(1, 8)):
            if i >= n:
                break
            name = f"img{i:04d}"
            (img_dir / f"{name}.jpg").write_bytes(b"\xff\xd8fake")
            cls = rng.sample(range(4), k)
            if cls:
                (lbl_dir / f"{name}.txt").write_text("".join(f"{c} 0.5 0.5 0.1 0.1\n" for c in cls))
            elif rng.random() < 0.5:
                (lbl_dir / f"{name}.txt").write_text("")
            rows.append([f"{name}.jpg", scene, f"g{g:03d}"])
            i += 1
        g += 1
    if rare_cell:   # 새 장면타입: 1종 3장 + 2종 2장
        for j in range(5):
            name = f"rare{j}"
            (img_dir / f"{name}.jpg").write_bytes(b"x")
            cls = [0] if j < 3 else [0, 1]
            (lbl_dir / f"{name}.txt").write_text("".join(f"{c} 0.5 0.5 0.1 0.1\n" for c in cls))
            rows.append([f"{name}.jpg", "rare_scene", f"rg{j}"])
    meta = root / "meta.csv"
    with open(meta, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["image", "scene_type", "capture_group"])
        w.writerows(rows)
    return img_dir, lbl_dir, meta


@pytest.fixture
def data(tmp_path):
    img, lbl, meta = make_dataset(tmp_path)
    return tmp_path, img, lbl, meta


@pytest.fixture
def result(data):
    _, img, lbl, meta = data
    return sb.make_split(img, lbl, meta, seed=42)


def run_script(root, img, lbl, meta, *extra):
    cmd = [sys.executable, str(SCRIPT), "--images", str(img), "--labels", str(lbl),
           "--meta", str(meta), "--split-dir", str(root / "splits"),
           "--out", str(root / "dataset"), "--class-names", ",".join(NAMES), *extra]
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------------------------------------------- 상수·단위 함수
def test_roles_targets():
    assert ROLES == {"train": 600, "val": 75, "test": 75, "holdout": 150}
    assert SPLITS == ["train", "val", "test", "holdout"]


def test_largest_remainder_sums_exactly():
    ratios = [v / sum(ROLES.values()) for v in ROLES.values()]
    for n in [1, 5, 7, 13, 100, 899, 900, 901]:
        out = sb.largest_remainder(n, ratios)
        assert sum(out) == n and all(x >= 0 for x in out)
    assert sb.largest_remainder(900, ratios) == list(ROLES.values())


@pytest.mark.parametrize("n, bucket", [(0, "0"), (1, "1"), (2, "2+"), (4, "2+")])
def test_cls_bucket(n, bucket):
    assert sb.cls_bucket(n) == bucket


def test_read_yolo_instances(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("0 .5 .5 .1 .1\n0 .2 .2 .1 .1\n2 .5 .5 .1 .1\n\n")
    assert sb.read_yolo_instances(p) == {0: 2, 2: 1}
    assert sb.read_yolo_instances(tmp_path / "none.txt") == {}


def test_load_class_names(tmp_path):
    assert sb.load_class_names(tmp_path) == []
    (tmp_path / "classes.txt").write_text("hair\nvinyl\n\n")
    assert sb.load_class_names(tmp_path) == ["hair", "vinyl"]


def test_load_meta_requires_columns(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text("image,scene\na.jpg,x\n")
    with pytest.raises(ValueError, match="열"):
        sb.load_meta(p)


# ---------------------------------------------------------------- make_split
def test_every_image_assigned_once(data, result):
    _, img, _, _ = data
    names = [r["image"] for r in result["records"]]
    assert len(names) == len(set(names)) == len(list(img.iterdir()))
    assert all(r["split"] in SPLITS for r in result["records"])


def test_no_capture_group_leakage(result):
    assert sb.find_leaks(result["records"]) == []


def test_split_sizes_close_to_target(result):
    cnt = Counter(r["split"] for r in result["records"])
    for k, t in ROLES.items():
        assert abs(cnt[k] - t) <= max(8, t * 0.1), f"{k}: {cnt[k]} vs {t}"


def test_scene_ratio_preserved(result):
    recs = result["records"]
    total = Counter(r["scene"] for r in recs)
    for k in SPLITS:
        rs = [r for r in recs if r["split"] == k]
        c = Counter(r["scene"] for r in rs)
        for s in total:
            assert abs(c[s] / len(rs) - total[s] / len(recs)) < 0.08, f"{k}/{s}"


def test_every_class_in_val_and_test(result):
    cc = sb.class_counts(result["records"])
    for c in range(4):
        assert cc[c]["val"] > 0 and cc[c]["test"] > 0, f"class {c}: {cc[c]}"


def test_seed_is_deterministic(data):
    _, img, lbl, meta = data
    key = lambda s: {r["image"]: r["split"] for r in sb.make_split(img, lbl, meta, seed=s)["records"]}
    assert key(7) == key(7)
    assert key(7) != key(8)


def test_small_cell_is_merged_within_scene(tmp_path):
    img, lbl, meta = make_dataset(tmp_path, n=300, rare_cell=True)
    res = sb.make_split(img, lbl, meta, min_cell=4)
    rare = [r for r in res["records"] if r["scene"] == "rare_scene"]
    assert {r["stratum"] for r in rare} == {"rare_scene|1"}      # 2+ (2장) → 1 (3장)
    assert any("rare_scene|2+" in m for m in res["merges"])


def test_missing_meta_row_fails(data):
    _, img, lbl, meta = data
    (img / "orphan.jpg").write_bytes(b"x")
    with pytest.raises(ValueError, match="orphan.jpg"):
        sb.make_split(img, lbl, meta)


def test_custom_roles(data):
    _, img, lbl, meta = data
    roles = {"train": 800, "val": 50, "test": 50, "holdout": 0}
    res = sb.make_split(img, lbl, meta, roles=roles)
    cnt = Counter(r["split"] for r in res["records"])
    assert cnt["holdout"] == 0
    assert abs(cnt["train"] - 800) <= 10


# ---------------------------------------------------------------- manifest·report
def test_manifest_roundtrip(tmp_path, result):
    p = tmp_path / "m.csv"
    sb.write_manifest(result["records"], p)
    rows = sb.read_manifest(p)
    assert {r["image"]: r["split"] for r in rows} == {r["image"]: r["split"] for r in result["records"]}


def test_read_manifest_rejects_bad(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("image,split\na.jpg,train\na.jpg,val\n")
    with pytest.raises(ValueError, match="중복"):
        sb.read_manifest(p)
    p.write_text("image,split\na.jpg,training\n")
    with pytest.raises(ValueError, match="split 값"):
        sb.read_manifest(p)


def test_report(tmp_path, result):
    p = tmp_path / "r.md"
    sb.write_report(result, p, NAMES)
    text = p.read_text(encoding="utf-8")
    assert "여러 split에 걸친 그룹: **0개**" in text
    assert "| hair |" in text


# ---------------------------------------------------------------- materialize·verify
@pytest.fixture
def built(tmp_path, data, result):
    _, img, lbl, _ = data
    p = tmp_path / "m.csv"
    sb.write_manifest(result["records"], p)
    rows = sb.read_manifest(p)
    out = tmp_path / "dataset"
    stats = sb.materialize(rows, img, lbl, out, NAMES)
    return rows, out, stats, lbl


def test_materialize_layout(built):
    rows, out, stats, _ = built
    cnt = Counter(r["split"] for r in rows)
    for s in SPLITS:
        assert stats[s]["images"] == cnt[s]
    assert sb.verify_dataset(out, rows) == []


def test_negative_gets_empty_label(built):
    rows, out, _, lbl = built
    neg = [r for r in rows if not (lbl / f"{Path(r['image']).stem}.txt").exists()]
    assert neg
    p = out / "labels" / neg[0]["split"] / f"{Path(neg[0]['image']).stem}.txt"
    assert p.exists() and p.read_text() == ""


def test_label_content_unchanged(built):
    rows, out, _, lbl = built
    for r in rows[:50]:
        src = lbl / f"{Path(r['image']).stem}.txt"
        if src.exists():
            assert (out / "labels" / r["split"] / src.name).read_text() == src.read_text()


def test_data_yaml(built):
    _, out, _, _ = built
    y = (out / "data.yaml").read_text(encoding="utf-8")
    for line in ["train: images/train", "val: images/val", "test: images/test",
                 "holdout: images/holdout", "nc: 4", "  0: hair", "  3: stone"]:
        assert line in y


def test_verify_detects_stray_file(built, data):
    rows, out, _, _ = built
    (out / "images" / "train" / "stray.jpg").write_bytes(b"x")
    assert sb.verify_dataset(out, rows)
    _, img, lbl, _ = data
    sb.materialize(rows, img, lbl, out, NAMES, clean=True)
    assert sb.verify_dataset(out, rows) == []


# ---------------------------------------------------------------- scripts/03_build_split.py
def test_script_end_to_end(data):
    root, img, lbl, meta = data
    res = run_script(root, img, lbl, meta)
    assert res.returncode == 0, res.stderr
    assert "[완료]" in res.stdout
    assert (root / "splits" / "split_manifest.csv").exists()
    assert (root / "splits" / "split_report.md").exists()
    assert (root / "dataset" / "data.yaml").exists()


def test_script_split_only(data):
    root, img, lbl, meta = data
    res = run_script(root, img, lbl, meta, "--split-only")
    assert res.returncode == 0, res.stderr
    assert (root / "splits" / "split_manifest.csv").exists()
    assert not (root / "dataset").exists()


def test_script_missing_input_message(tmp_path):
    res = subprocess.run([sys.executable, str(SCRIPT), "--images", str(tmp_path / "nope"),
                          "--labels", str(tmp_path), "--meta", str(tmp_path / "m.csv")],
                         capture_output=True, text=True)
    assert res.returncode != 0
    assert "입력 경로가 없습니다" in res.stderr