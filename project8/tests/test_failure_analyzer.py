import pytest

from src.failure_analyzer import box_iou


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