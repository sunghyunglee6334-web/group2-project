"""학습된 YOLO 모델을 같은 기준으로 평가하는 공통 모듈 (④ Evaluation 담당).
Baseline · Improved · Final 모델 모두 이 파일로 평가한다."""

from pathlib import Path

VALID_SPLITS = ("val", "test")


def check_inputs(model_path, data_yaml, split, allow_test=False):
    
    # (1) Weight 파일 존재 확인
    if not Path(model_path).is_file():
        raise FileNotFoundError(f"Weight 파일이 없습니다: {model_path}")
    # (2) dataset.yaml 존재 확인
    if not Path(data_yaml).is_file():
        raise FileNotFoundError(f"dataset.yaml 이 없습니다: {data_yaml}")
    # (3) split 값 확인   
    if split not in VALID_SPLITS:
        raise ValueError(f"split 은 {VALID_SPLITS} 중 하나여야 합니다. 받은 값: {split!r}")
    # (4) test split 은 allow_test=False 시 막는다
    if split == "test" and not allow_test:
        raise PermissionError(
            "Frozen Test 는 Final Model 을 정한 뒤에만 엽니다. "
            "정말 최종 평가라면 allow_test=True 를 넣어 주세요."
        )


def evaluate_detector(
    model_path: str,
    data_yaml: str,
    split: str = "val",
    imgsz: int = 640,
    allow_test: bool = False,
):
    """YOLO 모델을 한 split 에서 평가하고 Ultralytics metrics 객체를 돌려준다."""
    check_inputs(model_path, data_yaml, split, allow_test)

    from ultralytics import YOLO  # 실제 평가할 때만 불러온다
    model = YOLO(model_path)
    return model.val(
        data=data_yaml,
        split=split,
        imgsz=imgsz,
        plots=True,
    )


def summarize_overall(metrics):
    """전체 성능 4개를 dict 로 정리한다."""
    # TODO 3
    pass


def summarize_per_class(metrics):
    """Class 0~6 별 성능을 정리한다. 정답 0건인 Class 는 N/A."""
    # TODO 4
    pass


def save_metrics_csv(rows, out_path):
    """정리한 결과를 CSV 로 저장한다."""
    # TODO 5
    pass