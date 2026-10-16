"""Val 전체에서 실패 후보를 모아 비교 그림과 failure_analysis 초안을 만든다.
실행 (project8 폴더에서, compare_gt_pred.py 다음에): python scripts/09_collect_failures.py"""

import shutil
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluate_detector import save_metrics_csv        # noqa: E402
from src.failure_analyzer import analyze_image, count_types  # noqa: E402
from src.label_visualizer import visualize                # noqa: E402
from src.split_builder import CLASS_NAMES                 # noqa: E402

IMAGE_DIR = PROJECT_ROOT / "data" / "yolo" / "images" / "val"
LABEL_DIR = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"
PRED_DIR = PROJECT_ROOT / "runs" / "pred_val" / "labels"      # compare_gt_pred.py 결과
VAL_CSV = PROJECT_ROOT / "manifests" / "val.csv"
OUT_IMG = PROJECT_ROOT / "runs" / "failure_candidates"
SUMMARY_CSV = PROJECT_ROOT / "reports" / "failure_summary.csv"
DRAFT_CSV = PROJECT_ROOT / "reports" / "failure_analysis_draft.csv"
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
FAIL_TYPES = ("FN", "FP", "CLASS", "BBOX")                    # TP 는 실패가 아님

def class_name(class_id):
    """Class 번호 → 이름. 짝이 없으면(None) "none"."""
    if class_id is None:
        return "none"
    return CLASS_NAMES.get(class_id, str(class_id))


def load_val_info(val_csv):
    """val.csv 를 읽어 {이미지 이름(확장자 제외): {"source_dataset", "scene_type"}} 로 돌려준다."""
    df = pd.read_csv(val_csv, encoding="utf-8-sig")

    # 1 필요한 컬럼이 있는지 먼저 확인
    need = ["image_name", "source_dataset", "scene_type"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"val.csv 에 필요한 컬럼이 없습니다: {missing}")

    # 2 빈칸(NaN)은 빈 글자로
    df = df[need].fillna("")

    # 3 이름 → 정보 사전
    info = {}
    for name, source, scene in zip(df["image_name"], df["source_dataset"], df["scene_type"]):
        info[Path(name).stem] = {"source_dataset": source, "scene_type": scene}
    return info


def collect(images, info, label_dir=LABEL_DIR, pred_dir=PRED_DIR):
    """이미지마다 판정해서 (요약 줄 목록, 실패 박스 줄 목록) 을 돌려준다.
    요약은 실패 개수가 많은 이미지부터 정렬한다."""
    summary, fails = [], []
    for img in images:
        # 1 val.csv 정보 (없으면 빈칸)
        meta = info.get(img.stem, {"source_dataset": "", "scene_type": ""})

        # 2 판정과 개수
        results = analyze_image(label_dir / f"{img.stem}.txt", pred_dir / f"{img.stem}.txt")
        counts = count_types(results)
        n_fail = sum(counts[t] for t in FAIL_TYPES)

        # 3 요약표: 이미지 한 장 = 한 줄
        summary.append({"image": img.name, **meta, **counts, "n_fail": n_fail})

        # 4 초안표: 실패 박스 한 개 = 한 줄 (가이드 failure_analysis.csv 컬럼)
        for r in results:
            if r["failure_type"] == "TP":
                continue
            fails.append({
                "image": img.name, **meta,
                "failure_type": r["failure_type"],
                "ground_truth": class_name(r["gt_class"]),
                "prediction": class_name(r["pred_class"]),
                "confidence": "" if r["confidence"] is None else round(r["confidence"], 3),
                "iou": r["iou"],
                "suspected_cause": "", "evidence": "", "next_action": "",   # 사람이 채움
            })

    # 5 실패 많은 이미지부터
    summary.sort(key=lambda row: row["n_fail"], reverse=True)
    order = {row["image"]: i for i, row in enumerate(summary)}
    fails.sort(key=lambda row: order[row["image"]])
    return summary, fails


def main_type(row):
    """실패가 가장 많은 유형. 같으면 FAIL_TYPES 순서(FN 우선)."""
    return max(FAIL_TYPES, key=lambda t: (row[t], -FAIL_TYPES.index(t)))


def save_failure_images(summary_rows, image_dir=IMAGE_DIR, label_dir=LABEL_DIR,
                        pred_dir=PRED_DIR, out_dir=OUT_IMG):
    """실패가 있는 이미지만 비교 그림을 그려 유형별 폴더에 저장하고, 저장한 장수를 돌려준다."""
    if out_dir.exists():                 # 1 지난번 결과 지우기 (다시 돌려도 섞이지 않게)
        shutil.rmtree(out_dir)
    saved = 0
    for row in summary_rows:
        if row["n_fail"] == 0:           # 2 다 맞힌 이미지는 건너뜀
            continue
        stem = Path(row["image"]).stem
        visualize(image_dir / row["image"], label_dir / f"{stem}.txt",          # 3 GT 초록 + 예측 파랑
                  out_dir / main_type(row) / f"{stem}.jpg", CLASS_NAMES,
                  pred_txt=pred_dir / f"{stem}.txt")
        saved += 1
    return saved


def main():
    """준비물 확인 → 정보 읽기 → 판정 → CSV 2개 저장 → 그림 저장 → 요약 출력"""
    # 1 준비물
    for need in (IMAGE_DIR, LABEL_DIR, PRED_DIR, VAL_CSV):
        if not need.exists():
            sys.exit(f"아직 없습니다: {need.relative_to(PROJECT_ROOT)}\n"
                     "→ Split 결과와 compare_gt_pred.py 예측이 끝난 뒤 다시 실행하세요.")

    # 2 판정
    info = load_val_info(VAL_CSV)
    images = sorted(p for p in IMAGE_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    summary, fails = collect(images, info)

    # 3 저장
    save_metrics_csv(summary, SUMMARY_CSV)
    if fails:
        save_metrics_csv(fails, DRAFT_CSV)
    elif DRAFT_CSV.exists():                    # 실패 0건이면 예전 초안이 남지 않게 지움
        DRAFT_CSV.unlink()
    saved = save_failure_images(summary)

    # 4 화면 요약: 6일차 가설의 첫 단서
    total = Counter(r["failure_type"] for r in fails)
    print(f"Val {len(images)}장 중 실패가 있는 이미지 {saved}장")
    print("유형별:", {t: total.get(t, 0) for t in FAIL_TYPES})
    print("scene_type 별:")
    for (scene, kind), n in sorted(Counter((r["scene_type"], r["failure_type"]) for r in fails).items()):
        print(f"  {scene or '(빈칸)'} / {kind}: {n}")
    saved_files = [SUMMARY_CSV] + ([DRAFT_CSV] if fails else []) + [OUT_IMG]
    print("저장:", ", ".join(str(p.relative_to(PROJECT_ROOT)) for p in saved_files))

if __name__ == "__main__":
    main()