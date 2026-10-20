"""개선 실험 공통 기능 (⑤ Experiment 담당).

Baseline 조건(BASELINE_CONFIG)을 그대로 복사한 뒤 변수 '하나만' 바꿔서 실험 조건을 만든다.
학습은 src/train_detector.py 의 train_detector() 를 그대로 재사용한다.

    EXPERIMENTS 에 실험을 추가할 때는 changes 에 딱 1개만 넣는다.
"""
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

from src.project_config import (
    BASELINE_CONFIG,
    BASELINE_RUN_NAME,
    DATASET_VERSION,
    MANIFEST_DIR,
    MODEL_DIR,
    REPORT_DIR,
)

# 색 증강 기본값 (Ultralytics 8.4 기본값 · Baseline 학습 때도 이 값이 쓰였음)
#   hsv_h: 색상(Hue) 흔들기 · hsv_s: 채도(진하기) 흔들기 · hsv_v: 밝기 흔들기
AUG_DEFAULTS = {"hsv_h": 0.015, "hsv_s": 0.7, "hsv_v": 0.4}

# 실험 목록 (reports/improvement_experiment.md 와 같은 내용)
#   base   : 기준 실험 (없으면 Baseline). 이 실험 조건을 복사한 뒤 changes 만 바꾼다.
#   factor : 여러 값을 묶어 "요인 1개"로 바꿀 때만 쓴다 (예: 색 증강 = hsv_s + hsv_v)
EXPERIMENTS = {
    "exp001": {
        "changes": {"imgsz": 960},
        "reason": "small 이물 FN 36%(37/103) · large 5% → 640 축소 시 작은 이물 특징 손실 가설",
    },
    "exp002": {
        "changes": {"model_name": "yolo11s.pt"},
        "reason": "CLASS 오류 17개 · branch↔plastic↔leaf 혼동 (박스 IoU는 0.9 이상) → 모델 용량 부족 가설",
    },
    "exp003": {
        "changes": {"imgsz": 1280},
        "reason": "EXP001(960)에서 Baseline 대비 mAP50-95 +0.079 · 재현율 +0.041 → 해상도를 더 올리면 작은 이물 FN이 더 줄어드는지 확인",
    },
    "exp004": {
        "base": "exp003",
        "changes": {"model_name": "yolo11s.pt"},
        "reason": "EXP003(n·1280) KEEP 후 모델만 n→s · EXP002에서 Class 혼동(정밀도) 개선 확인 → 1280 위에서도 효과 있는지 확인",
    },
}
# 주의: 각 실험은 기준(base) 대비 요인 1개만 바꾼다.
#       exp004 는 base=exp003 이라 Baseline 대비로는 2개(imgsz + model)가 바뀐 누적 실험 → Final 후보에서 제외, 참고용

# experiment_log.csv 컬럼 (수행가이드 20.4 권장 필드)
LOG_COLUMNS = [
    "experiment_id", "date", "dataset_version", "model", "imgsz", "epochs", "batch", "seed",
    "changed_variable", "reason",
    "validation_precision", "validation_recall", "validation_map50", "validation_map50_95",
    "decision",
]


def base_config(exp_id, baseline=None, experiments=None):
    """이 실험의 기준 조건. base 가 있으면 그 실험 조건, 없으면 Baseline (+ 색 증강 기본값)"""
    baseline = BASELINE_CONFIG if baseline is None else baseline
    experiments = EXPERIMENTS if experiments is None else experiments
    if exp_id not in experiments:
        raise KeyError(f"등록되지 않은 실험입니다: {exp_id} (가능: {list(experiments)})")
    base = experiments[exp_id].get("base")
    if base is None:
        return dict(baseline, **{k: v for k, v in AUG_DEFAULTS.items() if k not in baseline})
    if base == exp_id:
        raise ValueError(f"{exp_id} 가 자기 자신을 기준으로 삼고 있습니다.")
    return build_config(base, baseline, experiments)[0]


def build_config(exp_id, baseline=None, experiments=None):
    """기준 조건 + 요인 1개 변경 = 실험 조건. 요인이 1개가 아니면 멈춘다."""
    experiments = EXPERIMENTS if experiments is None else experiments
    start = base_config(exp_id, baseline, experiments)
    exp = experiments[exp_id]
    changes = exp["changes"]

    # (1) 한 요인만 바꾸는지 확인 (factor 로 묶은 경우만 여러 값 허용)
    if not changes:
        raise ValueError(f"{exp_id}: 바꾸는 값이 없습니다.")
    if len(changes) > 1 and not exp.get("factor"):
        raise ValueError(f"한 번에 변수 1개만 바꿉니다. 지금 {len(changes)}개: {list(changes)} "
                         f"(한 요인으로 묶을 거면 factor 이름을 적으세요)")
    for key, value in changes.items():
        # (2) 기준에 있는 항목인지 확인 (오타 방지)
        if key not in start:
            raise KeyError(f"기준 조건에 없는 항목입니다: {key} (가능: {list(start)})")
        # (3) 실제로 값이 바뀌는지 확인
        if start[key] == value:
            raise ValueError(f"{key} 가 기준과 같습니다 ({value}). 바뀌는 게 없습니다.")

    cfg = dict(start, **changes)
    return cfg, exp.get("factor") or next(iter(changes))


def changed_text(exp_id, baseline=None, experiments=None):
    """'imgsz 640 -> 960' 같은 기록용 문자열 (기준이 Baseline 이 아니면 앞에 표시)"""
    experiments = EXPERIMENTS if experiments is None else experiments
    start = base_config(exp_id, baseline, experiments)
    exp = experiments[exp_id]
    text = ", ".join(f"{k} {start[k]} -> {v}" for k, v in exp["changes"].items())
    if exp.get("factor"):
        text = f"{exp['factor']}: {text}"
    if exp.get("base"):
        text = f"[기준 {exp['base']}] {text}"
    return text


def manifest_version(path):
    """06_train_baseline.py 와 같은 형식: '파일명 rows=N md5=앞8자리'"""
    path = Path(path)
    if not path.exists():
        return "없음"
    data = path.read_bytes()
    rows = data.count(b"\n") - 1  # 헤더 제외
    return f"{path.name} rows={rows} md5={hashlib.md5(data).hexdigest()[:8]}"


def check_same_data_as_baseline(run_info_path=None, manifest_dir=None):
    """Baseline 학습 때와 train/val manifest 가 같은지 확인. 다르면 비교가 무의미하므로 멈춘다."""
    run_info_path = Path(run_info_path or REPORT_DIR / "baseline_run_info.json")
    manifest_dir = Path(manifest_dir or MANIFEST_DIR)
    if not run_info_path.exists():
        raise FileNotFoundError(f"Baseline 학습 기록이 없습니다: {run_info_path}")

    info = json.loads(run_info_path.read_text(encoding="utf-8"))
    problems = []
    if info.get("dataset_version") != DATASET_VERSION:
        problems.append(f"dataset_version: baseline={info.get('dataset_version')} / 지금={DATASET_VERSION}")
    for key, name in (("train_manifest", "train.csv"), ("val_manifest", "val.csv")):
        now = manifest_version(manifest_dir / name)
        if info.get(key) != now:
            problems.append(f"{name}: baseline={info.get(key)} / 지금={now}")
    if problems:
        raise RuntimeError("Baseline 과 데이터가 다릅니다. 같은 조건 비교가 안 됩니다:\n  " + "\n  ".join(problems))
    return info


def weight_path(exp_id):
    """models/improved/exp001_best.pt"""
    return MODEL_DIR / "improved" / f"{exp_id}_best.pt"


def make_log_row(exp_id, cfg, changed, reason, metrics, decision="TBD"):
    """experiment_log.csv 한 줄"""
    return {
        "experiment_id": exp_id,
        "date": date.today().isoformat(),
        "dataset_version": DATASET_VERSION,
        "model": cfg["model_name"],
        "imgsz": cfg["imgsz"],
        "epochs": cfg["epochs"],
        "batch": cfg["batch"],
        "seed": cfg["seed"],
        "changed_variable": changed,
        "reason": reason,
        "validation_precision": metrics["precision"],
        "validation_recall": metrics["recall"],
        "validation_map50": metrics["map50"],
        "validation_map50_95": metrics["map50_95"],
        "decision": decision,
    }


def upsert_log(row, log_path=None):
    """experiment_log.csv 에 한 줄 추가. 같은 experiment_id 가 있으면 그 줄만 새 값으로 바꾼다.
    (다른 실험 줄은 지우지 않는다 → 실패한 실험도 남는다)"""
    log_path = Path(log_path or REPORT_DIR / "experiment_log.csv")
    rows = []
    if log_path.exists():
        with open(log_path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))

    replaced = False
    for i, old in enumerate(rows):
        if old["experiment_id"] == row["experiment_id"]:
            rows[i] = {k: row.get(k, "") for k in LOG_COLUMNS}
            replaced = True
    if not replaced:
        rows.append({k: row.get(k, "") for k in LOG_COLUMNS})

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return log_path


def baseline_log_row(metrics_csv=None):
    """reports/baseline_metrics.csv 의 Val 숫자로 Baseline 기준 줄을 만든다.
    학습 조건은 실제 학습 기록(BASELINE_CONFIG = run_info 와 같은 값)을 쓴다."""
    metrics_csv = Path(metrics_csv or REPORT_DIR / "baseline_metrics.csv")
    if not metrics_csv.exists():
        raise FileNotFoundError(f"Baseline 평가 결과가 없습니다: {metrics_csv}")
    with open(metrics_csv, newline="", encoding="utf-8-sig") as f:
        m = next(csv.DictReader(f))
    metrics = {k: m[k] for k in ("precision", "recall", "map50", "map50_95")}
    return make_log_row(BASELINE_RUN_NAME, BASELINE_CONFIG, "-", "비교 기준 (팀 공통 Baseline)",
                        metrics, decision="baseline")
