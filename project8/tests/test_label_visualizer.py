from src.label_visualizer import read_yolo_labels, yolo_to_xyxy
import numpy as np
import cv2
from src.label_visualizer import draw_boxes, visualize, GT_COLOR


def test_read_gt(tmp_path):
    txt = tmp_path / "a.txt"
    txt.write_text("1 0.5 0.5 0.2 0.4\n0 0.1 0.1 0.05 0.05\n")
    labels = read_yolo_labels(txt)
    assert len(labels) == 2
    assert labels[0] == (1, 0.5, 0.5, 0.2, 0.4, None)    # 정답이라 conf 없음


def test_read_empty_file(tmp_path):
    txt = tmp_path / "normal.txt"
    txt.write_text("")                                     # 정상 김치
    assert read_yolo_labels(txt) == []


def test_read_prediction_with_conf(tmp_path):
    txt = tmp_path / "pred.txt"
    txt.write_text("3 0.5 0.5 0.1 0.1 0.87\n")
    assert read_yolo_labels(txt)[0][5] == 0.87


def test_xyxy_center_box():
    assert yolo_to_xyxy(0.5, 0.5, 0.2, 0.4, 1000, 500) == (400, 150, 600, 350)


def test_xyxy_clipped_at_edge():
    x1, y1, x2, y2 = yolo_to_xyxy(0.02, 0.5, 0.1, 0.1, 1000, 500)   # 왼쪽 밖으로 삐져나감
    assert x1 == 0

NAMES = {0: "leaf_paper", 1: "plastic_stone_metal", 3: "insect"}


def test_draw_boxes_paints_gt_color():
    img = np.zeros((500, 1000, 3), dtype=np.uint8)              # 검은 빈 이미지
    draw_boxes(img, [(1, 0.5, 0.5, 0.2, 0.4, None)], NAMES, GT_COLOR)
    assert tuple(img[250, 400]) == GT_COLOR                      # 왼쪽 테두리는 초록
    assert tuple(img[250, 500]) == (0, 0, 0)                     # 박스 안은 그대로


def test_visualize_saves_file(tmp_path):
    img_path = tmp_path / "a.jpg"
    cv2.imwrite(str(img_path), np.full((500, 1000, 3), 128, dtype=np.uint8))
    gt = tmp_path / "a.txt"
    gt.write_text("1 0.5 0.5 0.2 0.4\n")
    pred = tmp_path / "a_pred.txt"
    pred.write_text("1 0.52 0.5 0.2 0.4 0.87\n")
    out = visualize(img_path, gt, tmp_path / "out" / "a_vis.jpg", NAMES, pred_txt=pred)
    assert out.is_file()


def test_visualize_shrinks_4k(tmp_path):
    img_path = tmp_path / "big.jpg"
    cv2.imwrite(str(img_path), np.zeros((2160, 3840, 3), dtype=np.uint8))
    gt = tmp_path / "big.txt"
    gt.write_text("")
    out = visualize(img_path, gt, tmp_path / "big_vis.jpg", NAMES)
    assert max(cv2.imread(str(out)).shape[:2]) == 1600          # 긴 변이 1600 으로


def test_visualize_missing_image(tmp_path):
    gt = tmp_path / "x.txt"
    gt.write_text("")