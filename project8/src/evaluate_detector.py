"""YOLO 평가 공통 함수 (baseline · 개선 실험에서 재사용)"""
from pathlib import Path

from ultralytics import YOLO

from src.project_config import CLASS_NAMES


def evaluate_detector(weights, data_yaml, split, imgsz, batch, project, name):
    """weights 를 data_yaml 의 split 으로 평가 -> (전체 지표 dict, Class 별 목록, 결과 폴더)"""
    weights, data_yaml = Path(weights), Path(data_yaml)
    for p in (weights, data_yaml):
        if not p.exists():
            raise FileNotFoundError(f"파일이 없습니다: {p}")

    metrics = YOLO(str(weights)).val(
        data=str(data_yaml),
        split=split,
        imgsz=imgsz,
        batch=batch,
        project=str(project),
        name=name,
        exist_ok=True,
        plots=True,
    )
    box = metrics.box
    overall = {
        "precision": round(float(box.mp), 4),
        "recall": round(float(box.mr), 4),
        "map50": round(float(box.map50), 4),
        "map50_95": round(float(box.map), 4),
    }

    per_class = []
    for i, cls in enumerate(metrics.ap_class_index):
        p, r, ap50, ap = box.class_result(i)
        per_class.append({
            "class_id": int(cls),
            "class_name": CLASS_NAMES[int(cls)],
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "map50": round(float(ap50), 4),
            "map50_95": round(float(ap), 4),
        })
    return overall, per_class, Path(metrics.save_dir)
