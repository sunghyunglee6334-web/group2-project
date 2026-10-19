"""갈변(Class 5) 정답 사진만 골라서, 정답 박스와 모델 예측을 같이 그려 비교한다.

- 입력: Val 중 라벨에 Class 5 가 있는 사진 (정답 갈변이 있는 사진만)
- 그림: runs/disease_check/<exp>/*.jpg
        정답 = 실선, 예측 = 점선 + 확신도 (둘 다 갈변만 그림)
- 표  : reports/<exp>_disease_check.csv
        정답 박스마다 "가장 많이 겹친 예측"의 IoU · 확신도 · 박스 크기 비교

확신도 기준을 일부러 낮게(기본 0.05) 둬서, 평소엔 안 보이는 약한 예측까지 본다.
Test · Bridge 는 사용하지 않는다 (Val 만).

    python scripts/10c_check_disease.py                 # exp005 · conf 0.05
    python scripts/10c_check_disease.py --exp exp004
"""
import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.experiment_runner import EXPERIMENTS, build_config, weight_path  # noqa: E402
from src.label_visualizer import read_yolo_labels, visualize  # noqa: E402
from src.project_config import CLASS_NAMES, REPORT_DIR, RUNS_DIR, YOLO_DIR  # noqa: E402

DISEASE = 5
IMG_EXTS = (".jpg", ".jpeg", ".png")


def iou(a, b):
    """(xc, yc, w, h) 두 박스의 IoU"""
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def center_inside(p, g):
    """예측 박스 중심이 정답 박스 안에 있나 (정답 안에 작게 찍힌 경우 찾기)"""
    return abs(p[0] - g[0]) <= g[2] / 2 and abs(p[1] - g[1]) <= g[3] / 2


def find_image(stem):
    for ext in IMG_EXTS:
        p = YOLO_DIR / "images" / "val" / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def write_only_disease(rows, path):
    """갈변 줄만 남긴 임시 TXT (그림에 갈변만 보이게)"""
    lines = []
    for r in rows:
        if r[0] == DISEASE:
            line = f"{r[0]} {r[1]:.6f} {r[2]:.6f} {r[3]:.6f} {r[4]:.6f}"
            if len(r) > 5 and r[5] is not None:
                line += f" {r[5]:.4f}"
            lines.append(line)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", default="exp005", choices=list(EXPERIMENTS))
    parser.add_argument("--conf", type=float, default=0.05)
    args = parser.parse_args()

    cfg, _ = build_config(args.exp)
    weight = weight_path(args.exp)
    if not weight.exists():
        raise FileNotFoundError(f"Weight 가 없습니다: {weight}")

    # 1. 갈변 정답이 있는 Val 사진 찾기
    label_dir = YOLO_DIR / "labels" / "val"
    targets = []
    for txt in sorted(label_dir.glob("*.txt")):
        if ":" in txt.name:  # Zone.Identifier 같은 꼬리표 파일 제외
            continue
        gt = read_yolo_labels(txt)
        if any(r[0] == DISEASE for r in gt):
            img = find_image(txt.stem)
            if img:
                targets.append((img, txt, gt))
    n_gt = sum(sum(1 for r in gt if r[0] == DISEASE) for _, _, gt in targets)
    print(f"갈변 정답이 있는 Val 사진 {len(targets)}장 · 갈변 정답 박스 {n_gt}개")

    # 2. 그 사진들만 예측 (확신도 낮게, 갈변만)
    from ultralytics import YOLO
    out_dir = RUNS_DIR / "disease_check" / args.exp
    pred_run = RUNS_DIR / "disease_check" / f"{args.exp}_pred"
    model = YOLO(str(weight))
    model.predict(source=[str(t[0]) for t in targets], imgsz=cfg["imgsz"], conf=args.conf,
                  classes=[DISEASE], save=False, save_txt=True, save_conf=True,
                  project=str(pred_run.parent), name=pred_run.name, exist_ok=True, verbose=False)

    # 3. 정답 박스마다 가장 많이 겹친 예측 찾기 + 그림 저장
    tmp = out_dir / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    rows = []
    for img, txt, gt in targets:
        pred_txt = pred_run / "labels" / f"{img.stem}.txt"
        pred = read_yolo_labels(pred_txt) if pred_txt.exists() else []
        pred = [p for p in pred if p[0] == DISEASE]
        for g in [r for r in gt if r[0] == DISEASE]:
            best = max(pred, key=lambda p: iou(g[1:5], p[1:5]), default=None)
            best_iou = iou(g[1:5], best[1:5]) if best else 0.0
            inside = [p for p in pred if center_inside(p[1:5], g[1:5])]
            if best is None:
                verdict = "예측 없음"
            elif best_iou >= 0.5:
                verdict = "찾음 (IoU≥0.5)"
            elif best_iou >= 0.1 or inside:
                verdict = "근처 · 박스 어긋남"
                if best_iou < 0.1:  # 정답 안에 작게 찍힌 경우는 그 예측을 대표로
                    best = max(inside, key=lambda p: p[5] or 0)
                    best_iou = iou(g[1:5], best[1:5])
            else:
                verdict = "엉뚱한 곳"
            rows.append({
                "image": img.name,
                "gt_w": round(g[3], 4), "gt_h": round(g[4], 4),
                "gt_area_pct": round(g[3] * g[4] * 100, 3),
                "n_pred_in_image": len(pred),
                "best_iou": round(best_iou, 3),
                "best_conf": round(best[5], 3) if best and best[5] is not None else "",
                "pred_w": round(best[3], 4) if best else "", "pred_h": round(best[4], 4) if best else "",
                "verdict": verdict,
            })
        visualize(img, write_only_disease(gt, tmp / "gt.txt"), out_dir / img.name, CLASS_NAMES,
                  pred_txt=write_only_disease(pred, tmp / "pred.txt"))

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    out_csv = REPORT_DIR / f"{args.exp}_disease_check.csv"
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # 4. 요약
    from collections import Counter
    cnt = Counter(r["verdict"] for r in rows)
    print(f"\n[{args.exp} · conf {args.conf}] 갈변 정답 {len(rows)}개")
    for k in ("찾음 (IoU≥0.5)", "근처 · 박스 어긋남", "엉뚱한 곳", "예측 없음"):
        print(f"  {k:<14} {cnt.get(k, 0)}개")
    print(f"\n표 : {out_csv.relative_to(PROJECT_ROOT)}")
    print(f"그림: {out_dir.relative_to(PROJECT_ROOT)}/  (정답 = 실선, 예측 = 점선)")


if __name__ == "__main__":
    main()
