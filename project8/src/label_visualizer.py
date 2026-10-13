"""YOLO 라벨(정답/예측)을 이미지 위에 박스로 그리는 도구"""

from pathlib import Path

GT_COLOR = (0, 200, 0)       # 정답: 초록 (OpenCV 는 BGR 순서)
PRED_COLOR = (255, 120, 0)   # 예측: 파랑


def read_yolo_labels(txt_path):
    """YOLO TXT 를 읽어 [(class_id, xc, yc, w, h, conf), ...] 로 돌려준다."""
    labels = []
    text = Path(txt_path).read_text(encoding="utf-8")
    for line in text.splitlines():
        parts = line.split()
        if not parts:                              # 빈 줄은 건너뜀
            continue
        class_id = int(parts[0])
        xc, yc, w, h = map(float, parts[1:5])
        conf = float(parts[5]) if len(parts) > 5 else None   # 예측 TXT 에만 있음
        labels.append((class_id, xc, yc, w, h, conf))
    return labels


def yolo_to_xyxy(xc, yc, w, h, img_w, img_h):
    """비율 좌표 → 픽셀 좌표 (x1, y1, x2, y2). 이미지 밖으로 나가지 않게 자른다."""
    x1 = (xc - w / 2) * img_w
    y1 = (yc - h / 2) * img_h
    x2 = (xc + w / 2) * img_w
    y2 = (yc + h / 2) * img_h
    # 이미지 범위(0 ~ 너비-1, 0 ~ 높이-1) 안으로 자르고 정수로
    x1 = int(max(0, min(x1, img_w - 1)))
    y1 = int(max(0, min(y1, img_h - 1)))
    x2 = int(max(0, min(x2, img_w - 1)))
    y2 = int(max(0, min(y2, img_h - 1)))
    return x1, y1, x2, y2


def draw_boxes(image, labels, class_names, color, show_conf=False):
    """이미지 위에 박스와 Class 이름을 그린다."""
    # TODO C
    pass


def visualize(image_path, gt_txt, out_path, class_names, pred_txt=None):
    """한 장을 그려 저장한다. pred_txt 를 주면 정답과 예측을 함께 그린다."""
    # TODO D
    pass