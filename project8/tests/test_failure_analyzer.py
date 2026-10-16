import pytest

from src.failure_analyzer import box_iou
from src.failure_analyzer import box_iou, match_boxes
from src.failure_analyzer import analyze_image, box_iou, count_types, match_boxes

def test_iou_same_box():
    """완전히 같은 박스 → 1"""
    assert box_iou((0.5, 0.5, 0.2, 0.2), (0.5, 0.5, 0.2, 0.2)) == pytest.approx(1.0)


def test_iou_no_overlap():
    """멀리 떨어진 박스 → 0"""
    assert box_iou((0.2, 0.2, 0.1, 0.1), (0.8, 0.8, 0.1, 0.1)) == 0.0


def test_iou_half_shift():
    """가로로 반 칸 밀림: 겹친 0.02 ÷ 합친 0.06 = 1/3"""
    assert box_iou((0.5, 0.5, 0.2, 0.2), (0.6, 0.5, 0.2, 0.2)) == pytest.approx(1 / 3)


def test_iou_inside():
    """작은 박스가 큰 박스 안: 0.04 ÷ 0.16 = 0.25 → TP 아님, BBOX 후보"""
    assert box_iou((0.5, 0.5, 0.4, 0.4), (0.5, 0.5, 0.2, 0.2)) == pytest.approx(0.25)

def gt(cls, xc, yc, w, h):
    """정답 박스 한 줄 (conf 없음)"""
    return (cls, xc, yc, w, h, None)


def pred(cls, xc, yc, w, h, conf):
    """예측 박스 한 줄"""
    return (cls, xc, yc, w, h, conf)


def types(results):
    return sorted(r["failure_type"] for r in results)


def test_tp():
    r = match_boxes([gt(1, .5, .5, .2, .2)], [pred(1, .5, .5, .2, .2, .9)])
    assert types(r) == ["TP"]


def test_class_error():
    r = match_boxes([gt(1, .5, .5, .2, .2)], [pred(2, .5, .5, .2, .2, .9)])
    assert types(r) == ["CLASS"]
    assert r[0]["gt_class"] == 1 and r[0]["pred_class"] == 2


def test_bbox_error():
    """작은 박스가 정답 안에 들어감 (IoU 0.25)"""
    r = match_boxes([gt(1, .5, .5, .4, .4)], [pred(1, .5, .5, .2, .2, .9)])
    assert types(r) == ["BBOX"]


def test_fp_normal_kimchi():
    """정답 0개(정상 김치)인데 예측이 나옴"""
    r = match_boxes([], [pred(0, .3, .3, .1, .1, .6)])
    assert types(r) == ["FP"]
    assert r[0]["gt_class"] is None


def test_fn_missed():
    """정답이 있는데 예측 0개"""
    r = match_boxes([gt(3, .5, .5, .05, .05)], [])
    assert types(r) == ["FN"]


def test_duplicate_box_is_fp():
    """한 물체에 박스 2개 → 확신도 높은 쪽이 TP, 나머지는 FP"""
    r = match_boxes([gt(1, .5, .5, .2, .2)],
                    [pred(1, .5, .5, .2, .2, .6), pred(1, .51, .5, .2, .2, .9)])
    assert types(r) == ["FP", "TP"]
    assert [x for x in r if x["failure_type"] == "TP"][0]["confidence"] == .9


def test_mixed():
    """정답 2개, 예측 2개: 하나 맞힘 + 하나 놓침 + 엉뚱한 곳 하나"""
    r = match_boxes([gt(1, .2, .2, .1, .1), gt(2, .8, .8, .1, .1)],
                    [pred(1, .2, .2, .1, .1, .8), pred(0, .5, .1, .1, .1, .4)])
    assert types(r) == ["FN", "FP", "TP"]


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_analyze_basic(tmp_path):
    """정답 1개를 맞히고, 확신도 0.1 짜리 헛박스는 버려진다"""
    gt = write(tmp_path / "gt.txt", "1 0.5 0.5 0.2 0.2\n")
    pr = write(tmp_path / "pred.txt", "1 0.5 0.5 0.2 0.2 0.9\n0 0.1 0.1 0.1 0.1 0.1\n")
    assert count_types(analyze_image(gt, pr)) == {"TP": 1, "FP": 0, "FN": 0, "CLASS": 0, "BBOX": 0}


def test_analyze_conf_min(tmp_path):
    """기준을 0.05 로 낮추면 헛박스가 FP 로 잡힌다"""
    gt = write(tmp_path / "gt.txt", "1 0.5 0.5 0.2 0.2\n")
    pr = write(tmp_path / "pred.txt", "1 0.5 0.5 0.2 0.2 0.9\n0 0.1 0.1 0.1 0.1 0.1\n")
    assert count_types(analyze_image(gt, pr, conf_min=0.05))["FP"] == 1


def test_analyze_no_pred_file(tmp_path):
    """예측 TXT 가 없으면 예측 0개 → 정답은 모두 FN"""
    gt = write(tmp_path / "gt.txt", "2 0.5 0.5 0.1 0.1\n3 0.2 0.2 0.1 0.1\n")
    assert count_types(analyze_image(gt, tmp_path / "none.txt"))["FN"] == 2


def test_analyze_normal_kimchi(tmp_path):
    """정상 김치: 빈 정답 TXT + 예측 1개 → FP 1"""
    gt = write(tmp_path / "gt.txt", "")
    pr = write(tmp_path / "pred.txt", "0 0.3 0.3 0.1 0.1 0.7\n")
    assert count_types(analyze_image(gt, pr))["FP"] == 1


def test_analyze_gt_missing(tmp_path):
    """정답 TXT 자체가 없으면 멈춘다"""
    with pytest.raises(FileNotFoundError):
        analyze_image(tmp_path / "no_gt.txt", tmp_path / "pred.txt")