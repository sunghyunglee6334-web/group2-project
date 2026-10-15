"""정답(GT)과 예측(Prediction) 박스를 IoU 로 짝지어 실패 유형을 판정하는 도구
6일차 Failure Analysis 에서 failure_analysis.csv 초안을 만드는 데 쓴다."""

from pathlib import Path

from src.label_visualizer import read_yolo_labels

IOU_MATCH = 0.5      # 이 이상 겹치면 "같은 물체를 가리킨다"고 본다
IOU_LOW = 0.1        # 이 이상 ~ IOU_MATCH 미만이면 BBOX 오류 후보
CONF_MIN = 0.25      # 이보다 확신도가 낮은 예측은 버린다


def box_iou(a, b):
    """비율 좌표 박스 두 개(xc, yc, w, h)의 IoU 를 0~1 로 돌려준다."""
    # 1 중심·크기 → 꼭짓점
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2

    # 2·3 겹친 부분 (안 겹치면 너비나 높이가 0)
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h

    # 4 합친 넓이
    union = a[2] * a[3] + b[2] * b[3] - inter
    if union <= 0:                 # 크기 0 짜리 박스가 들어와도 0 으로 나누지 않게
        return 0.0

    # 5
    return inter / union


def match_boxes(gts, preds, iou_match=IOU_MATCH, iou_low=IOU_LOW):
    """한 이미지의 정답·예측 박스를 짝지어 박스마다 판정 결과를 돌려준다.
    결과: [{"failure_type", "gt_class", "pred_class", "confidence", "iou"}, ...]"""
    # TODO B
    pass


def analyze_image(gt_txt, pred_txt, conf_min=CONF_MIN):
    """TXT 두 개를 읽어 match_boxes 를 돌린다. 예측 TXT 가 없으면 예측 0개로 본다."""
    # TODO C
    pass


def count_types(results):
    """판정 결과를 유형별로 센다. 예: {"TP": 3, "FP": 1, "FN": 0, "CLASS": 0, "BBOX": 1}"""
    # TODO D
    pass