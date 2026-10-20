"""experiment_runner 가 '한 변수만 바꾸기' 규칙을 지키는지 확인한다. YOLO · GPU 없이 돌아간다."""
import csv
import json

import pytest

from src.experiment_runner import (
    AUG_DEFAULTS,
    build_config,
    changed_text,
    check_same_data_as_baseline,
    manifest_version,
    upsert_log,
)

BASE = {"model_name": "yolo11n.pt", "epochs": 70, "imgsz": 640, "batch": 8, "patience": 30, "seed": 42}
FULL = dict(BASE, **AUG_DEFAULTS)  # Baseline + 색 증강 기본값


def test_exp001_changes_only_imgsz():
    cfg, key = build_config("exp001", baseline=BASE)
    assert key == "imgsz"
    assert cfg["imgsz"] == 960
    # 나머지는 전부 Baseline 과 같아야 함
    assert {k: v for k, v in cfg.items() if k != "imgsz"} == {k: v for k, v in FULL.items() if k != "imgsz"}


def test_exp002_changes_only_model():
    cfg, key = build_config("exp002", baseline=BASE)
    assert key == "model_name"
    assert cfg["model_name"] == "yolo11s.pt"
    assert cfg["imgsz"] == 640  # 해상도는 Baseline 그대로
    assert {k: v for k, v in cfg.items() if k != "model_name"} == {k: v for k, v in FULL.items() if k != "model_name"}


def test_exp003_changes_only_imgsz_to_1280():
    cfg, key = build_config("exp003", baseline=BASE)
    assert key == "imgsz"
    assert cfg["imgsz"] == 1280
    assert cfg["model_name"] == "yolo11n.pt"  # 모델은 Baseline 그대로
    assert {k: v for k, v in cfg.items() if k != "imgsz"} == {k: v for k, v in FULL.items() if k != "imgsz"}


def test_exp004_based_on_exp003_changes_only_model():
    cfg, key = build_config("exp004", baseline=BASE)
    exp003, _ = build_config("exp003", baseline=BASE)
    assert key == "model_name"
    assert cfg["imgsz"] == 1280  # exp003 조건 그대로
    assert cfg["model_name"] == "yolo11s.pt"
    diff = {k for k in cfg if cfg[k] != exp003[k]}
    assert diff == {"model_name"}  # exp003 대비 모델만 다름


def test_exp004_changed_text():
    assert changed_text("exp004", baseline=BASE) == "[기준 exp003] model_name yolo11n.pt -> yolo11s.pt"


def test_factor_group_allows_multiple():
    exps = {"ok": {"factor": "색", "changes": {"hsv_s": 0.3, "hsv_v": 0.2}, "reason": ""}}
    cfg, factor = build_config("ok", baseline=BASE, experiments=exps)
    assert factor == "색" and cfg["hsv_s"] == 0.3


def test_two_changes_rejected():
    exps = {"bad": {"changes": {"imgsz": 960, "batch": 4}, "reason": ""}}
    with pytest.raises(ValueError):
        build_config("bad", baseline=BASE, experiments=exps)


def test_same_value_rejected():
    exps = {"same": {"changes": {"imgsz": 640}, "reason": ""}}
    with pytest.raises(ValueError):
        build_config("same", baseline=BASE, experiments=exps)


def test_typo_key_rejected():
    exps = {"typo": {"changes": {"img_size": 960}, "reason": ""}}
    with pytest.raises(KeyError):
        build_config("typo", baseline=BASE, experiments=exps)


def test_changed_text():
    assert changed_text("exp001", baseline=BASE) == "imgsz 640 -> 960"


def test_manifest_mismatch_stops(tmp_path):
    (tmp_path / "train.csv").write_text("h\na\n")
    (tmp_path / "val.csv").write_text("h\nb\n")
    info = {"dataset_version": "kimchi_v1",
            "train_manifest": manifest_version(tmp_path / "train.csv"),
            "val_manifest": "val.csv rows=75 md5=xxxxxxxx"}  # 일부러 다르게
    run_info = tmp_path / "run_info.json"
    run_info.write_text(json.dumps(info))
    with pytest.raises(RuntimeError):
        check_same_data_as_baseline(run_info, tmp_path)


def test_upsert_keeps_other_rows(tmp_path):
    log = tmp_path / "experiment_log.csv"
    upsert_log({"experiment_id": "baseline_v1", "validation_recall": 0.592}, log)
    upsert_log({"experiment_id": "exp001", "validation_recall": 0.6}, log)
    upsert_log({"experiment_id": "exp001", "validation_recall": 0.65}, log)  # 다시 평가 → 덮어씀
    with open(log, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert [r["experiment_id"] for r in rows] == ["baseline_v1", "exp001"]
    assert rows[1]["validation_recall"] == "0.65"
