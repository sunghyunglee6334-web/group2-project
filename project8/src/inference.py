"""Final Model로 단일 이미지를 추론하고 결과를 반환하거나 시각화한다.

Validation/Test 평가와 분리된 이미지 추론 기능이다. 데이터셋 split을 읽거나
``model.val()``을 호출하지 않으므로 Bridge Holdout을 사용하지 않는다.
파일 저장·배치 실행은 이 기능을 호출하는 ``scripts/14_predict_images.py``가 담당한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from .label_visualizer import draw_boxes
from .project_config import CLASS_NAMES, IMG_EXTS, MODEL_DIR, PRED_CONF

FINAL_WEIGHT = MODEL_DIR / "final" / "final_best.pt"
FINAL_IMGSZ = 1280  # reports/final_model_selection.md 에 기록된 EXP003 학습 크기


@dataclass(frozen=True)
class Detection:
    """한 검출 결과. bbox_xyxy는 원본 이미지 기준 픽셀 좌표(x1, y1, x2, y2)."""

    bbox_xyxy: tuple[float, float, float, float]
    class_id: int
    class_name: str
    confidence: float


class ImageInference:
    """Final Weight를 한 번 로드해 여러 이미지를 추론하는 객체."""

    def __init__(
        self,
        weight_path: str | Path = FINAL_WEIGHT,
        *,
        imgsz: int = FINAL_IMGSZ,
        conf: float = PRED_CONF,
    ) -> None:
        weight = Path(weight_path).expanduser()
        if not weight.is_file():
            raise FileNotFoundError(f"모델 Weight 파일이 없습니다: {weight}")
        if imgsz <= 0:
            raise ValueError(f"imgsz는 양수여야 합니다: {imgsz}")
        if not 0.0 <= conf <= 1.0:
            raise ValueError(f"conf는 0부터 1 사이여야 합니다: {conf}")

        # 기존 Evaluation 코드와 동일하게 Ultralytics YOLO Weight를 로드한다.
        from ultralytics import YOLO

        self.weight_path = weight
        self.imgsz = imgsz
        self.conf = conf
        self.model = YOLO(str(weight))

    def predict(self, image_path: str | Path) -> list[Detection]:
        """이미지 한 장을 추론해 좌표·Class ID·이름·Confidence를 반환한다."""
        image = Path(image_path).expanduser()
        if not image.is_file():
            raise FileNotFoundError(f"입력 이미지가 없습니다: {image}")
        if image.suffix.lower() not in IMG_EXTS:
            raise ValueError(f"지원하지 않는 이미지 형식입니다: {image.suffix}")

        # Evaluation의 model.val()과 분리된 predict 경로이며 저장은 호출자가 선택한다.
        results = self.model.predict(
            source=str(image),
            imgsz=self.imgsz,
            conf=self.conf,
            save=False,
            verbose=False,
        )
        if not results or results[0].boxes is None:
            return []

        boxes = results[0].boxes
        xyxy = boxes.xyxy.detach().cpu().tolist()
        class_ids = boxes.cls.detach().cpu().tolist()
        confidences = boxes.conf.detach().cpu().tolist()

        return [
            Detection(
                bbox_xyxy=tuple(float(v) for v in coordinates),
                class_id=int(class_id),
                class_name=CLASS_NAMES.get(int(class_id), f"class_{int(class_id)}"),
                confidence=float(confidence),
            )
            for coordinates, class_id, confidence in zip(xyxy, class_ids, confidences)
        ]

    @staticmethod
    def save_visualization(
        image_path: str | Path,
        detections: list[Detection],
        output_path: str | Path,
    ) -> Path:
        """원본 이미지를 보존하며 BBox·Class·Confidence 시각화 파일을 저장한다."""
        image = Path(image_path).expanduser()
        output = Path(output_path).expanduser()
        if not image.is_file():
            raise FileNotFoundError(f"입력 이미지가 없습니다: {image}")
        if image.resolve() == output.resolve():
            raise ValueError("출력 경로가 원본 이미지와 같습니다. 원본 보호를 위해 저장을 중단합니다.")

        canvas = cv2.imread(str(image))
        if canvas is None:
            raise ValueError(f"이미지를 열 수 없습니다: {image}")
        height, width = canvas.shape[:2]

        # 기존 label_visualizer의 Class 색상·표시 방식을 재사용한다.
        yolo_labels = []
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox_xyxy
            yolo_labels.append((
                detection.class_id,
                ((x1 + x2) / 2) / width,
                ((y1 + y2) / 2) / height,
                (x2 - x1) / width,
                (y2 - y1) / height,
                detection.confidence,
            ))
        draw_boxes(canvas, yolo_labels, CLASS_NAMES, show_conf=True)

        output.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output), canvas):
            raise OSError(f"시각화 이미지를 저장하지 못했습니다: {output}")
        return output
