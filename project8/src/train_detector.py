"""YOLO 학습 공통 함수 (smoke · baseline · 개선 실험에서 재사용)"""
from pathlib import Path

from ultralytics import YOLO


def train_detector(model_name, data_yaml, epochs, imgsz, batch, seed, project, name, **extra):
    """YOLO 학습 후 결과 폴더(project/name) 를 돌려준다."""
    data_yaml = Path(data_yaml)
    if not data_yaml.exists():
        raise FileNotFoundError(f"Dataset YAML 이 없습니다: {data_yaml}")

    model = YOLO(model_name)
    model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        seed=seed,
        project=str(project),
        name=name,
        exist_ok=True,
        **extra,
    )
    return Path(project) / name
