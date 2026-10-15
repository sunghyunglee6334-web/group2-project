import pytest

from src.failure_analyzer import box_iou
from src.failure_analyzer import box_iou, match_boxes

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