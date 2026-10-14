"""YOLO 라벨(정답/예측)을 이미지 위에 박스로 그리는 도구

- 박스 색 = Class별 색 (CLASS_COLORS)
- 정답(GT) = 실선, 예측(Pred) = 점선 + 확신도
- 이미지 왼쪽 위에 그 사진에 나온 Class의 색 범례를 붙인다
"""

from pathlib import Path
import cv2

GT_COLOR = (0, 200, 0)       # (예전 방식) 정답 한 가지 색: 초록
PRED_COLOR = (255, 120, 0)   # (예전 방식) 예측 한 가지 색: 파랑

# Class별 색 (OpenCV는 BGR 순서). 색약인 사람도 구분하기 쉬운 Okabe-Ito 계열
CLASS_COLORS = {
    0: (178, 114, 0),    # 파랑
    1: (0, 159, 230),    # 주황
    2: (115, 158, 0),    # 청록
    3: (60, 30, 200),    # 진홍
    4: (128, 128, 128),  # 회색 (사용 안 함: 고무장갑 → Class 1로 합침)
    5: (167, 121, 204),  # 연보라·분홍
    6: (150, 40, 110),   # 진보라
}


def class_color(class_id):
    """Class 번호 → 색. 표에 없는 번호도 항상 같은 색이 나오게 번호로 만든다."""
    if class_id in CLASS_COLORS:
        return CLASS_COLORS[class_id]
    return ((class_id * 67) % 200 + 30, (class_id * 131) % 200 + 30, (class_id * 197) % 200 + 30)


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


def draw_dashed_rect(image, p1, p2, color, thickness, dash=None):
    """점선 사각형 (예측 박스용)"""
    dash = dash or max(8, thickness * 4)
    (x1, y1), (x2, y2) = p1, p2
    for a, b, fixed, horizontal in ((x1, x2, y1, True), (x1, x2, y2, True),
                                     (y1, y2, x1, False), (y1, y2, x2, False)):
        for s in range(a, b, dash * 2):
            e = min(s + dash, b)
            if horizontal:
                cv2.line(image, (s, fixed), (e, fixed), color, thickness)
            else:
                cv2.line(image, (fixed, s), (fixed, e), color, thickness)


def draw_boxes(image, labels, class_names, color=None, show_conf=False, label_below=False,
               dashed=False):
    """이미지 위에 박스와 Class 이름을 그린다.
    color=None 이면 Class별 색(CLASS_COLORS), 색을 주면 모든 박스를 그 색으로 (예전 방식).
    label_below=True 면 이름표를 박스 아래에 붙인다 (정답 이름표와 겹치지 않게).
    dashed=True 면 점선 박스 (예측 표시용)."""
    img_h, img_w = image.shape[:2]
    thickness, font_scale = draw_style(image)
    font = cv2.FONT_HERSHEY_SIMPLEX

    for class_id, xc, yc, w, h, conf in labels:
        c = color if color is not None else class_color(class_id)

        # ① 박스 (정답 = 실선, 예측 = 점선)
        x1, y1, x2, y2 = yolo_to_xyxy(xc, yc, w, h, img_w, img_h)
        if dashed:
            draw_dashed_rect(image, (x1, y1), (x2, y2), c, thickness)
        else:
            cv2.rectangle(image, (x1, y1), (x2, y2), c, thickness)

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
        cv2.rectangle(image, (x1, top), (x1 + tw + 4, top + box_h), c, -1)
        cv2.putText(image, text, (x1 + 2, top + th + 2), font, font_scale,
                    (255, 255, 255), max(1, thickness // 2), cv2.LINE_AA)
    return image


def draw_legend(image, class_ids, class_names, with_pred=False):
    """왼쪽 위에 Class 색 범례를 그린다. (cv2 글꼴은 한글이 안 나와서 영어/숫자로 표기)"""
    if not class_ids and not with_pred:
        return image
    thickness, font_scale = draw_style(image)
    font = cv2.FONT_HERSHEY_SIMPLEX
    fs = font_scale * 0.9
    lines = [(class_color(c), class_names.get(c, str(c)) + f" ({c})") for c in sorted(class_ids)]
    if with_pred:
        lines.append((None, "GT: solid  /  Pred: dashed"))
    (_, th), base = cv2.getTextSize("Ag", font, fs, 1)
    row = th + base + 8
    width = max(cv2.getTextSize(t, font, fs, 1)[0][0] for _, t in lines) + row + 20
    height = row * len(lines) + 10
    overlay = image.copy()
    cv2.rectangle(overlay, (5, 5), (5 + width, 5 + height), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)          # 반투명 검은 바탕
    for i, (c, t) in enumerate(lines):
        y = 10 + i * row
        x = 12
        if c is not None:
            cv2.rectangle(image, (x, y + 2), (x + th, y + th + 2), c, -1)   # 색 네모
            x += th + 8
        cv2.putText(image, t, (x, y + th), font, fs, (255, 255, 255), max(1, thickness // 2), cv2.LINE_AA)
    return image


def visualize(image_path, gt_txt, out_path, class_names, pred_txt=None, max_side=1600,
              color_by_class=True, legend=True):
    """한 장을 그려 저장하고 저장 경로를 돌려준다.
    color_by_class=True  : Class별 색, 정답 = 실선 / 예측 = 점선 (+확신도)
    color_by_class=False : 예전 방식 (정답 초록, 예측 파랑)
    4K 원본은 너무 크므로 긴 변을 max_side 로 줄여 저장한다."""
    image = cv2.imread(str(image_path))
    if image is None:                                   # ① 이미지 읽기 실패 확인
        raise FileNotFoundError(f"이미지를 읽을 수 없습니다: {image_path}")

    gt = read_yolo_labels(gt_txt)                       # ② 정답
    draw_boxes(image, gt, class_names, None if color_by_class else GT_COLOR)
    pred = []
    if pred_txt is not None and Path(pred_txt).is_file():                        # ③ 예측
        pred = read_yolo_labels(pred_txt)
        draw_boxes(image, pred, class_names, None if color_by_class else PRED_COLOR,
                   show_conf=True, label_below=True, dashed=color_by_class)

    h, w = image.shape[:2]                              # ④ 크기 줄이기
    scale = max_side / max(h, w)
    if scale < 1:
        image = cv2.resize(image, (round(w * scale), round(h * scale)),
                           interpolation=cv2.INTER_AREA)

    if legend and color_by_class:                       # ⑤ 범례 (줄인 뒤에 그려야 글자가 안 작아짐)
        ids = {c for c, *_ in gt} | {c for c, *_ in pred}
        draw_legend(image, ids, class_names, with_pred=bool(pred))

    out_path = Path(out_path)                           # ⑥ 저장
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out_path), image):
        raise IOError(f"이미지를 저장하지 못했습니다: {out_path}")
    return out_path