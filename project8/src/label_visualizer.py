"""YOLO 라벨(정답/예측)을 이미지 위에 박스로 그리는 도구"""

from pathlib import Path
import cv2

GT_COLOR = (0, 200, 0)       # 정답: 초록
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


def draw_style(image):
    """이미지 크기에 맞춰 선 굵기와 글자 크기를 정한다. (4K → 굵기 4, 글자 1.5배)"""
    short = min(image.shape[:2])              # 짧은 변 (4K 면 2160)
    thickness = max(2, round(short / 500))    # 최소 2px
    font_scale = max(0.5, short / 1400)       # 최소 0.5배
    return thickness, font_scale


def draw_boxes(image, labels, class_names, color, show_conf=False, label_below=False):
    """이미지 위에 박스와 Class 이름을 그린다.
    label_below=True 면 이름표를 박스 아래에 붙인다 (정답 이름표와 겹치지 않게)."""
    img_h, img_w = image.shape[:2]
    thickness, font_scale = draw_style(image)
    font = cv2.FONT_HERSHEY_SIMPLEX

    for class_id, xc, yc, w, h, conf in labels:
        # ① 박스
        x1, y1, x2, y2 = yolo_to_xyxy(xc, yc, w, h, img_w, img_h)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

        # ② 이름표 글자: 예측이면 확신도도 붙인다
        name = class_names.get(class_id, str(class_id))
        text = f"{name} {conf:.2f}" if (show_conf and conf is not None) else name

        # ③ 이름표 위치: 기본은 박스 위, 예측은 박스 아래
        (tw, th), base = cv2.getTextSize(text, font, font_scale, thickness)
        box_h = th + base + 4
        if label_below:
            top = y2 if y2 + box_h < img_h else y2 - box_h
        else:
            top = y1 - box_h if y1 - box_h >= 0 else y1

        # ④ 색 배경 + 흰 글자 (어떤 사진 위에서도 잘 읽히게)
        cv2.rectangle(image, (x1, top), (x1 + tw + 4, top + box_h), color, -1)
        cv2.putText(image, text, (x1 + 2, top + th + 2), font, font_scale,
                    (255, 255, 255), max(1, thickness // 2), cv2.LINE_AA)
    return image


def visualize(image_path, gt_txt, out_path, class_names, pred_txt=None, max_side=1600):
    """한 장을 그려 저장하고 저장 경로를 돌려준다.
    정답은 초록, pred_txt 를 주면 예측은 파랑(+확신도)으로 함께 그린다.
    4K 원본은 너무 크므로 긴 변을 max_side 로 줄여 저장한다."""
    image = cv2.imread(str(image_path))
    if image is None:                                   # ① 이미지 읽기 실패 확인
        raise FileNotFoundError(f"이미지를 읽을 수 없습니다: {image_path}")

    draw_boxes(image, read_yolo_labels(gt_txt), class_names, GT_COLOR)          # ② 정답
    if pred_txt is not None and Path(pred_txt).is_file():                        # ③ 예측
        draw_boxes(image, read_yolo_labels(pred_txt), class_names, PRED_COLOR,
                   show_conf=True, label_below=True)

    h, w = image.shape[:2]                              # ④ 크기 줄이기
    scale = max_side / max(h, w)
    if scale < 1:
        image = cv2.resize(image, (round(w * scale), round(h * scale)),
                           interpolation=cv2.INTER_AREA)

    out_path = Path(out_path)                           # ⑤ 저장
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out_path), image):
        raise IOError(f"이미지를 저장하지 못했습니다: {out_path}")
    return out_path