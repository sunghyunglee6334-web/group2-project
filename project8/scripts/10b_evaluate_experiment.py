"""개선 실험 평가: Baseline 과 같은 Validation 75장으로 실험별로 따로 평가한다.

평가는 ④ Evaluation 의 src/evaluate_detector.py 를 그대로 사용한다 (Baseline 과 같은 방법).
각 모델은 자기가 학습한 imgsz 로 평가한다 (Baseline 640 / EXP001 960 / EXP002 640).
Frozen Test 는 열지 않는다 (split = val 고정).

실험마다 결과가 따로 저장된다 (서로 덮어쓰지 않음):
    reports/exp001_metrics.csv · exp001_class_metrics.csv · figures/exp001_*.png
    reports/exp002_metrics.csv · exp002_class_metrics.csv · figures/exp002_*.png
    reports/experiment_log.csv   ← baseline_v1 / exp001 / exp002 가 한 줄씩

    python scripts/10b_evaluate_experiment.py                 # 학습이 끝난 실험 전부
    python scripts/10b_evaluate_experiment.py --exp exp001    # 하나만
    python scripts/10b_evaluate_experiment.py --exp exp004    # 기준(exp001) 숫자도 같이 출력
"""
import argparse
import csv
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluate_detector import (  # noqa: E402
    evaluate_detector,
    save_metrics_csv,
    summarize_overall,
    summarize_per_class,
)
from src.experiment_runner import (  # noqa: E402
    EXPERIMENTS,
    baseline_log_row,
    build_config,
    changed_text,
    make_log_row,
    upsert_log,
    weight_path,
)
from src.project_config import DATASET_VERSION, DATASET_YAML, FIGURE_DIR, REPORT_DIR, RUNS_DIR  # noqa: E402

METRIC_NAMES = (("precision", "P"), ("recall", "R"), ("map50", "mAP50"), ("map50_95", "mAP50-95"))


def copy_figure(src, dst):
    if Path(src).is_file():
        FIGURE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        print("  그림 저장:", Path(dst).relative_to(PROJECT_ROOT))
    else:
        print("  그림 없음(건너뜀):", src)


def evaluate_one(exp_id):
    """실험 하나 평가. 결과는 exp_id 이름의 파일에만 저장한다."""
    cfg, _ = build_config(exp_id)
    weight = weight_path(exp_id)
    print("=" * 60)
    print(f"[{exp_id}] {changed_text(exp_id)} · 평가 imgsz={cfg['imgsz']}")
    if not weight.exists():
        print(f"[{exp_id}] Weight 가 없어서 건너뜀: {weight.relative_to(PROJECT_ROOT)} (먼저 10_train_experiment.py)")
        return None, None

    # 1. 같은 Validation 으로 평가 (결과 폴더: runs/val/<exp>)
    metrics = evaluate_detector(
        str(weight), str(DATASET_YAML),
        split="val", imgsz=cfg["imgsz"],
        project=RUNS_DIR / "val", name=exp_id,
    )

    # 2. 전체 · Class별 결과 저장 (baseline_metrics.csv 와 같은 형식)
    overall = summarize_overall(metrics)
    row = {"model_version": exp_id, "dataset_version": DATASET_VERSION, "split": "val",
           "model": cfg["model_name"], "imgsz": cfg["imgsz"], "batch": cfg["batch"],
           "epochs": cfg["epochs"], "seed": cfg["seed"], **overall}
    print("  저장:", save_metrics_csv(row, REPORT_DIR / f"{exp_id}_metrics.csv").relative_to(PROJECT_ROOT))
    per_class = summarize_per_class(metrics)
    print("  저장:", save_metrics_csv(per_class, REPORT_DIR / f"{exp_id}_class_metrics.csv").relative_to(PROJECT_ROOT))

    # 3. experiment_log.csv: 이 실험 줄만 추가 · 갱신 (다른 실험 줄은 그대로)
    upsert_log(make_log_row(exp_id, cfg, changed_text(exp_id), EXPERIMENTS[exp_id]["reason"], overall))

    # 4. 그림 복사
    copy_figure(Path(metrics.save_dir) / "confusion_matrix.png",
                FIGURE_DIR / f"{exp_id}_confusion_matrix.png")
    copy_figure(RUNS_DIR / exp_id / "results.png", FIGURE_DIR / f"{exp_id}_results.png")
    return overall, per_class


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", default="all", choices=["all", *EXPERIMENTS])
    args = parser.parse_args()

    # Baseline 기준 줄 (reports/baseline_metrics.csv 숫자)
    base = baseline_log_row()
    upsert_log(base)

    exp_ids = list(EXPERIMENTS) if args.exp == "all" else [args.exp]
    overall, per_class = {}, {}
    for exp_id in exp_ids:
        o, c = evaluate_one(exp_id)
        if o is not None:
            overall[exp_id], per_class[exp_id] = o, c
    print("\n저장:", (REPORT_DIR / "experiment_log.csv").relative_to(PROJECT_ROOT))

    if not overall:
        print("평가한 실험이 없습니다.")
        return

    # 기준이 Baseline 이 아닌 실험(exp004 등)은 그 기준 실험 숫자도 같이 보여준다
    for exp_id in list(overall):
        base_id = EXPERIMENTS[exp_id].get("base")
        base_csv = REPORT_DIR / f"{base_id}_metrics.csv" if base_id else None
        if base_csv and base_csv.exists() and base_id not in overall:
            with open(base_csv, newline="", encoding="utf-8-sig") as f:
                m = next(csv.DictReader(f))
            overall = {base_id: {k: m[k] for k, _ in METRIC_NAMES}, **overall}
            print(f"\n※ {exp_id} 의 기준은 {base_id} → {base_id} 숫자도 같이 표시 (reports/{base_id}_metrics.csv)")

    # 5. Baseline 과 실험들을 나란히 출력 (각 실험은 Baseline 대비 차이)
    print("\n[같은 Validation 75장 비교] 괄호 = Baseline 대비 차이")
    print(f"{'':<10}{'Baseline':>10}" + "".join(f"{e:>18}" for e in overall))
    for k, name in METRIC_NAMES:
        b = float(base[f"validation_{k}"])
        cells = "".join(f"{float(o[k]):>10.3f} ({float(o[k]) - b:+.3f})" for o in overall.values())
        print(f"{name:<10}{b:>10.3f}{cells}")

    print("\n[Class별 Recall]")
    print(f"{'':<26}" + "".join(f"{e:>10}" for e in per_class))
    first = next(iter(per_class.values()))
    for i, r in enumerate(first):
        cells = "".join(f"{str(rows[i]['recall']):>10}" for rows in per_class.values())
        print(f"{r['class_id']} {r['class_name']:<24}{cells}")


if __name__ == "__main__":
    main()
