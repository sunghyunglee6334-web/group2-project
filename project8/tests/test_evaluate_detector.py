"""check_inputs가 잘못된 입력을 제대로 막는지 확인한다. YOLO 없이 돌아간다."""
import pytest
from src.evaluate_detector import check_inputs
from types import SimpleNamespace
from src.evaluate_detector import summarize_overall
from src.evaluate_detector import summarize_per_class


@pytest.fixture
def fake_files(tmp_path):
    """시험용 가짜 Weight 와 yaml 을 임시 폴더에 만든다 (진짜 파일은 건드리지 않음)."""
    weight = tmp_path / "fake.pt"
    yaml = tmp_path / "dataset.yaml"
    weight.write_text("")
    yaml.write_text("")
    return str(weight), str(yaml)


def test_weight_missing(fake_files):
    _, yaml = fake_files
    with pytest.raises(FileNotFoundError):
        check_inputs("models/없는파일.pt", yaml, "val")


def test_wrong_split(fake_files):
    weight, yaml = fake_files
    with pytest.raises(ValueError):
        check_inputs(weight, yaml, "validation")


def test_test_is_locked(fake_files):
    weight, yaml = fake_files
    with pytest.raises(PermissionError):
        check_inputs(weight, yaml, "test")


def test_test_unlocked(fake_files):
    weight, yaml = fake_files
    check_inputs(weight, yaml, "test", allow_test=True)   # 에러 없으면 통과


def test_val_ok(fake_files):
    weight, yaml = fake_files
    check_inputs(weight, yaml, "val")                     # 에러 없으면 통과


def fake_metrics():
    """model.val() 결과와 같은 모양의 가짜 성적표."""
    box = SimpleNamespace(mp=0.75, mr=0.6, map50=0.68123456, map=0.41)
    return SimpleNamespace(box=box)


def test_summarize_overall_keys():
    result = summarize_overall(fake_metrics())
    assert list(result) == ["precision", "recall", "map50", "map50_95"]


def test_summarize_overall_values():
    result = summarize_overall(fake_metrics())
    assert result["precision"] == 0.75
    assert result["recall"] == 0.6
    assert result["map50"] == 0.6812      # 소수점 4자리로 반올림됐는지
    assert result["map50_95"] == 0.41


def fake_metrics_per_class():
    """Class 4 정답이 0건이라 성적표에서 빠진 상황을 흉내 낸다."""
    measured = [0, 1, 2, 3, 5, 6]                      # 4 가 없음
    scores = {                                          # 칸 위치 → (P, R, mAP50, mAP50-95)
        0: (0.8, 0.7, 0.75, 0.5),
        1: (0.6, 0.5, 0.55, 0.3),
        2: (0.7, 0.6, 0.65, 0.4),
        3: (0.5, 0.4, 0.45, 0.2),
        4: (0.9, 0.85, 0.88, 0.6),                      # ← 이건 Class 5 의 점수
        5: (0.65, 0.6, 0.62, 0.35),
    }
    box = SimpleNamespace(ap_class_index=measured, class_result=lambda i: scores[i])
    names = {0: "leaf_paper", 1: "plastic_stone_metal", 2: "branch", 3: "insect",
             4: "rubber_glove_unused", 5: "disease_browning", 6: "green_onion_pepper"}
    return SimpleNamespace(box=box, names=names)


def test_per_class_has_all_7():
    rows = summarize_per_class(fake_metrics_per_class())
    assert [r["class_id"] for r in rows] == [0, 1, 2, 3, 4, 5, 6]


def test_class4_is_na():
    rows = summarize_per_class(fake_metrics_per_class())
    assert rows[4]["precision"] == "N/A"
    assert rows[4]["map50"] == "N/A"


def test_class5_gets_its_own_score():
    rows = summarize_per_class(fake_metrics_per_class())
    assert rows[5]["class_name"] == "disease_browning"
    assert rows[5]["precision"] == 0.9                  # 4번째 칸의 점수가 Class 5 에 붙어야 함