"""3번 산출물: 대표 실패 사례 CSV + 대표 실패 이미지

실행 : python scripts/12_failure_deliverables.py
입력 : reports/failure_analysis_draft.csv (09 결과), runs/compare_val/*.jpg (compare_gt_pred 결과)
출력 : reports/failure_analysis.csv, demo/failure_analysis/*.jpg
기준 : Validation 75장 · conf 0.25 · IoU 0.5 (failure_analyzer.py 와 같음)
"""
import shutil
from pathlib import Path

import cv2
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "reports" / "failure_analysis_draft.csv"
COMPARE_DIR = ROOT / "runs" / "compare_val"
OUT_CSV = ROOT / "reports" / "failure_analysis.csv"
DEMO_DIR = ROOT / "demo" / "failure_analysis"

COLUMNS = ["image", "source_dataset", "scene_type", "failure_type", "ground_truth", "prediction",
           "confidence", "suspected_cause", "evidence", "next_action"]
CHECK = " [사진 확인 후 보완]"
# main val.csv 의 eval_exclude (pHash 중복) → 대표 사례로 고르지 않음
EXCLUDE = {"250513_022020042401.jpg", "250513_022057115759.jpg",
           "250513_022131908234.jpg", "250513_022144941639.jpg"}

# 대표 사례 고르는 규칙: 파일 이름 앞부분, 조건, 개수, 정렬 기준, 원인·근거·다음 실험
CASES = [
    dict(tag="fn_small_leaf_paper", n=2, where={"failure_type": "FN", "ground_truth": "leaf_paper"},
         cause="small_object",
         evidence="leaf_paper FN 8개가 모두 small (small 10개 중 8개 놓침, fn_by_size.csv)",
         action="imgsz 640→960 후 leaf_paper small FN 비교"),
    dict(tag="fn_disease_browning", n=2, where={"failure_type": "FN", "ground_truth": "disease_browning"},
         cause="small_object+rare_class",
         evidence="disease_browning 14개 중 FN 11개, Class 5 예측 0개 (Train 객체 170개, 60.6% small)",
         action="imgsz 960 후 변화 확인, 개선 없으면 Class 5 데이터 보강 검토"),
    dict(tag="fn_branch", n=1, where={"failure_type": "FN", "ground_truth": "branch"},
         cause="small_object",
         evidence="branch FN 37개 (놓친 비율 small 26% · medium 24% · large 7%)",
         action="imgsz 960 후 branch small·medium FN 비교"),
    dict(tag="fn_plastic", n=1, where={"failure_type": "FN", "ground_truth": "plastic_stone_metal"},
         cause="small_object",
         evidence="plastic_stone_metal FN 7개 (놓친 비율 small 23% · medium 15% · large 0%)",
         action="imgsz 960 후 plastic small FN 비교"),
    dict(tag="fp_normal_kimchi", n=1, where={"failure_type": "FP", "scene_type": "normal_kimchi"},
         sort="confidence", cause="background_confusion",
         evidence="이물 없는 정상 김치를 이물로 검출 (normal_kimchi FP 2개)",
         action="정상 장면 FP 변화 비교, 이후 conf 기준 조정 검토"),
    dict(tag="fp_kimchi", n=3, where={"failure_type": "FP", "scene_type": "kimchi_with_target"},
         sort="confidence", cause="background_confusion",
         evidence="FP 93개 중 75개가 kimchi_with_target, 80개가 IoU 0 (정답과 전혀 안 겹침)",
         action="imgsz 960 후 IoU 0 FP 수 비교, 이후 conf 기준 조정 검토"),
    dict(tag="fp_object_only", n=1, where={"failure_type": "FP", "scene_type": "object_only"},
         sort="confidence", cause="duplicate_or_class_confusion",
         evidence="object_only FP 16개",
         action="같은 이물에 박스가 겹쳐 나오는지 확인"),
    dict(tag="class_browning", n=2, where={"failure_type": "CLASS", "ground_truth": "disease_browning"},
         sort="confidence", cause="class_similarity+rare_class",
         evidence="Class 5 CLASS 3개 모두 다른 Class로 예측, 위치는 맞음 (CLASS IoU 중앙값 0.93)",
         action="Class 5 데이터 보강 후보"),
    dict(tag="class_other", n=2, where={"failure_type": "CLASS"}, not_gt="disease_browning",
         sort="confidence", cause="class_similarity",
         evidence="CLASS 17개 IoU 중앙값 0.928 → 위치는 맞고 Class만 틀림",
         action="혼동 행렬로 어떤 Class끼리 헷갈리는지 비교"),
    dict(tag="bbox", n=3, where={"failure_type": "BBOX"}, sort="iou", ascending=True,
         cause="localization_error",
         evidence="BBOX 17개 모두 IoU 0.1~0.5 (중앙값 0.32), 작은 이물은 몇 px만 어긋나도 IoU 급락",
         action="imgsz 960 후 IoU 0.5 이상으로 오르는지 비교"),
]


def pick(df, case, used):
    """조건에 맞는 행 중 n개를 고른다. 이미 쓴 사진은 되도록 피한다."""
    m = pd.Series(True, index=df.index)
    for k, v in case["where"].items():
        m &= df[k] == v
    if "not_gt" in case:
        m &= df["ground_truth"] != case["not_gt"]
    cand = df[m & ~df["image"].isin(EXCLUDE)]
    if "sort" in case:
        cand = cand.sort_values(case["sort"], ascending=case.get("ascending", False), na_position="last")
    fresh = cand[~cand["image"].isin(used)].drop_duplicates("image")
    rest = cand[cand["image"].isin(used)].drop_duplicates("image")
    return pd.concat([fresh, rest]).head(case["n"])


def save_demo(src, dst, label):
    """비교 그림 위에 실패 유형 띠를 붙여 저장한다. (cv2 는 한글이 안 나와서 영어)"""
    img = cv2.imread(str(src))
    if img is None:
        return False
    bar = max(40, img.shape[0] // 18)
    out = cv2.copyMakeBorder(img, bar, 0, 0, 0, cv2.BORDER_CONSTANT, value=(30, 30, 30))
    cv2.putText(out, label, (12, int(bar * 0.72)), cv2.FONT_HERSHEY_SIMPLEX, bar / 48,
                (255, 255, 255), 2, cv2.LINE_AA)
    return cv2.imwrite(str(dst), out)


def main():
    df = pd.read_csv(DRAFT, encoding="utf-8-sig")
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)
    DEMO_DIR.mkdir(parents=True)

    rows, used, missing = [], set(), []
    for case in CASES:
        for i, (_, r) in enumerate(pick(df, case, used).iterrows(), start=1):
            used.add(r["image"])
            name = f"{case['tag']}_{i:02d}.jpg"
            conf = "" if pd.isna(r["confidence"]) else f"{r['confidence']:.3f}"
            label = f"{r['failure_type']} | GT: {r['ground_truth']} / Pred: {r['prediction']} {conf}"
            if not save_demo(COMPARE_DIR / f"{Path(r['image']).stem}.jpg", DEMO_DIR / name, label):
                missing.append(r["image"])
            rows.append({**{c: r[c] for c in COLUMNS[:6]}, "confidence": conf,
                         "suspected_cause": case["cause"],
                         "evidence": f"{case['evidence']} · 그림: demo/failure_analysis/{name}{CHECK}",
                         "next_action": case["action"]})

    out = pd.DataFrame(rows, columns=COLUMNS)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"대표 사례 {len(out)}건 → {OUT_CSV.relative_to(ROOT)}")
    print(out["failure_type"].value_counts().to_dict())
    print(f"대표 이미지 → {DEMO_DIR.relative_to(ROOT)} ({len(out) - len(missing)}장)")
    if missing:
        print("비교 그림 없음:", missing)


if __name__ == "__main__":
    main()
