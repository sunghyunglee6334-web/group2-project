"""check_inputs 가 잘못된 입력을 제대로 막는지 확인한다. YOLO 없이 돌아간다."""
import pytest
from src.evaluate_detector import check_inputs


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