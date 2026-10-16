"""정답(GT)과 예측(Prediction) 박스를 IoU 로 짝지어 실패 유형을 판정하는 도구
6일차 Failure Analysis 에서 failure_analysis.csv 초안을 만드는 데 쓴다."""

from pathlib import Path

from src.label_visualizer import read_yolo_labels

IOU_MATCH = 0.5  # 이 이상 겹치면 "같은 물체를 가리킨다"고 본다
IOU_LOW = 0.1  # 이 이상 ~ IOU_MATCH 미만이면 BBOX 오류 후보
CONF_MIN = 0.25  # 이보다 확신도가 낮은 예측은 버린다
FAILURE_TYPES = ("TP", "FP", "FN", "CLASS", "BBOX")


def box_iou(a, b):
    """두 박스 a, b 의 IoU 를 계산한다. a, b 는 (x_center, y_center, width, height)"""
    # 1 중심·크기 → 꼭짓점
    ax1, ay1, ax2, ay2 = (
        a[0] - a[2] / 2,
        a[1] - a[3] / 2,
        a[0] + a[2] / 2,
        a[1] + a[3] / 2,
    )
    bx1, by1, bx2, by2 = (
        b[0] - b[2] / 2,
        b[1] - b[3] / 2,
        b[0] + b[2] / 2,
        b[1] + b[3] / 2,
    )

    # 2·3 겹친 부분 (안 겹치면 너비나 높이가 0)
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h

    # 4 합친 넓이
    union = a[2] * a[3] + b[2] * b[3] - inter
    if union <= 0:  # 크기 0 짜리 박스가 들어와도 0 으로 나누지 않게
        return 0.0

    # 5
    return inter / union


def match_boxes(gts, preds, iou_match=IOU_MATCH, iou_low=IOU_LOW):
    """한 이미지의 정답·예측 박스를 짝지어 박스마다 판정 결과를 돌려준다.
    gts, preds: [(class_id, xc, yc, w, h, conf), ...]  (정답의 conf 는 None)
    결과: [{"failure_type", "gt_class", "pred_class", "confidence", "iou"}, ...]"""
    results = []
    used = set()  # 이미 짝이 정해진 정답 번호

    # 1 확신도가 높은 예측부터
    for pred in sorted(preds, key=lambda p: p[5] or 0, reverse=True):
        p_cls, p_box, conf = pred[0], pred[1:5], pred[5]

        # 2 아직 짝이 없는 정답 중 가장 많이 겹치는 것 찾기
        best_i, best_iou = None, 0.0
        for i, gt in enumerate(gts):
            if i in used:
                continue
            iou = box_iou(p_box, gt[1:5])
            if iou > best_iou:
                best_i, best_iou = i, iou

        # 3 판정
        g_cls = gts[best_i][0] if best_i is not None else None
        if best_iou >= iou_match:
            kind = "TP" if p_cls == g_cls else "CLASS"
        elif best_iou >= iou_low and p_cls == g_cls:
            kind = "BBOX"
        else:
            kind = "FP"

        if kind == "FP":
            g_cls = None  # FP 는 짝지은 정답이 없다
        else:
            used.add(best_i)  # 이 정답은 짝이 생겼다

        results.append(
            {
                "failure_type": kind,
                "gt_class": g_cls,
                "pred_class": p_cls,
                "confidence": conf,
                "iou": round(best_iou, 3),
            }
        )

    # 4 끝까지 짝이 없는 정답 → FN
    for i, gt in enumerate(gts):
        if i not in used:
            results.append(
                {
                    "failure_type": "FN",
                    "gt_class": gt[0],
                    "pred_class": None,
                    "confidence": None,
                    "iou": 0.0,
                }
            )
    return results


def analyze_image(gt_txt, pred_txt, conf_min=CONF_MIN):
    """TXT 두 개를 읽어 match_boxes 를 돌린다. 예측 TXT 가 없으면 예측 0개로 본다."""
    gt_txt, pred_txt = Path(gt_txt), Path(pred_txt)

    # 1 정답 TXT 는 반드시 있어야 한다 (정상 김치는 "빈 파일"로 있음)
    if not gt_txt.is_file():
        raise FileNotFoundError(f"정답 TXT 가 없습니다: {gt_txt}")
    gts = read_yolo_labels(gt_txt)

    # 2 예측 TXT 는 없을 수 있다 (YOLO 는 박스가 0개면 파일을 만들지 않음)
    preds = read_yolo_labels(pred_txt) if pred_txt.is_file() else []

    # 3 확신도가 낮은 예측은 버린다
    preds = [p for p in preds if p[5] is None or p[5] >= conf_min]

    return match_boxes(gts, preds)


def count_types(results):
    """판정 결과를 유형별로 센다. 예: {"TP": 3, "FP": 1, "FN": 0, "CLASS": 0, "BBOX": 1}"""
    counts = {t: 0 for t in FAILURE_TYPES}  # 0건인 유형도 0 으로 보이게
    for r in results:
        counts[r["failure_type"]] += 1
    return counts
