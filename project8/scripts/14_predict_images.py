"""Final Model로 승인된 시연 이미지를 추론하고 결과를 저장한다.

실행 (project8 폴더에서):
    python scripts/14_predict_images.py
    python scripts/14_predict_images.py --input data/test_detection/sample.jpg

기본 출력:
    demo/prediction_images/              시각화 이미지
    demo/prediction_images/inference_results.csv  검출·모델·기준값·처리시간 기록
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference import FINAL_IMGSZ, FINAL_WEIGHT, Detection, ImageInference  # noqa: E402
from src.project_config import IMG_EXTS, PRED_CONF  # noqa: E402

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "demo" / "prediction_images"
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "test_detection"
BLOCKED_PATH_PARTS = {"train", "val", "validation", "test", "fr_test", "frozen_test", "bridge_holdout"}
CSV_COLUMNS = [
    "model_weight", "confidence_threshold", "imgsz", "input_image", "output_image",
    "inference_seconds", "detection_count", "detection_index",
    "class_id", "class_name", "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
]


def collect_images(input_path: Path) -> list[Path]:
    """단일 이미지 또는 폴더 바로 아래의 지원 이미지 목록을 반환한다."""
    if not input_path.exists():
        raise FileNotFoundError(f"입력 경로가 없습니다: {input_path}")
    if input_path.is_file():
        if input_path.suffix.lower() not in IMG_EXTS:
            raise ValueError(f"지원하지 않는 이미지 형식입니다: {input_path.suffix}")
        return [input_path]

    images = sorted(
        path for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in IMG_EXTS
    )
    if not images:
        raise FileNotFoundError(f"입력 폴더에 지원되는 이미지가 없습니다: {input_path}")
    return images


def validate_input_scope(images: list[Path]) -> None:
    """학습·평가 split은 막고, 별도로 지정한 test_detection 시연 폴더는 허용한다."""
    demo_root = DEFAULT_INPUT_DIR.resolve()
    for image in images:
        parts = {part.casefold() for part in image.parent.parts}
        blocked = parts & BLOCKED_PATH_PARTS
        blocked.update(
            part for part in parts
            if part.startswith(("train_", "val_", "test_", "fr_test_", "frozen_test_", "bridge_holdout_"))
        )
        try:
            image.resolve().relative_to(demo_root)
            in_demo_folder = True
        except ValueError:
            in_demo_folder = False
        if in_demo_folder:
            blocked.discard("test_detection")
        if blocked:
            names = ", ".join(sorted(blocked))
            raise ValueError(f"분할 데이터({names})는 Detection 시연 입력으로 사용할 수 없습니다: {image}")


def detection_rows(
    image_path: Path,
    output_path: Path,
    detections: list[Detection],
    elapsed: float,
    *,
    weight_path: Path,
    conf: float,
    imgsz: int,
) -> list[dict[str, object]]:
    """이미지별 기록을 검출 1건당 한 행으로 만든다 (미검출도 이미지 행 유지)."""
    def display_path(path: Path) -> str:
        try:
            return path.expanduser().resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        except ValueError:
            # 프로젝트 외부 입력의 개인 PC 절대경로는 CSV에 남기지 않는다.
            return path.name

    common = {
        "model_weight": display_path(weight_path),
        "confidence_threshold": conf,
        "imgsz": imgsz,
        "input_image": display_path(image_path),
        "output_image": display_path(output_path),
        "inference_seconds": round(elapsed, 6),
        "detection_count": len(detections),
    }
    if not detections:
        return [{**common, "detection_index": "", "class_id": "", "class_name": "",
                 "confidence": "", "bbox_x1": "", "bbox_y1": "", "bbox_x2": "", "bbox_y2": ""}]

    rows = []
    for index, detection in enumerate(detections, start=1):
        x1, y1, x2, y2 = detection.bbox_xyxy
        rows.append({
            **common,
            "detection_index": index,
            "class_id": detection.class_id,
            "class_name": detection.class_name,
            "confidence": round(detection.confidence, 6),
            "bbox_x1": round(x1, 3),
            "bbox_y1": round(y1, 3),
            "bbox_x2": round(x2, 3),
            "bbox_y2": round(y2, 3),
        })
    return rows


def write_results(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Final Model로 이미지 Detection을 수행합니다.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_DIR,
                        help="이미지 한 장 또는 폴더 (기본: data/test_detection)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="시각화 이미지를 저장할 폴더 (기본: demo/prediction_images)")
    parser.add_argument("--conf", type=float, default=PRED_CONF,
                        help=f"검출 Confidence 기준 (기본: {PRED_CONF})")
    parser.add_argument("--imgsz", type=int, default=FINAL_IMGSZ,
                        help=f"추론 입력 크기 (기본: {FINAL_IMGSZ})")
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    output_dir = args.output.expanduser().resolve()
    if input_path.is_dir() and input_path == output_dir:
        parser.error("출력 폴더가 입력 폴더와 같습니다. 입력 이미지를 보호하기 위해 별도 경로를 지정하세요.")
    if input_path.is_file() and (output_dir / input_path.name).resolve() == input_path:
        parser.error("결과 이미지 경로가 입력 원본과 같습니다. 원본 보호를 위해 별도 출력 폴더를 지정하세요.")

    images = collect_images(input_path)
    try:
        validate_input_scope(images)
    except ValueError as exc:
        parser.error(str(exc))
    engine = ImageInference(weight_path=FINAL_WEIGHT, imgsz=args.imgsz, conf=args.conf)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for image_path in images:
        started = time.perf_counter()
        detections = engine.predict(image_path)
        elapsed = time.perf_counter() - started

        output_path = output_dir / image_path.name
        saved_path = engine.save_visualization(image_path, detections, output_path)
        rows.extend(detection_rows(
            image_path,
            saved_path,
            detections,
            elapsed,
            weight_path=engine.weight_path,
            conf=engine.conf,
            imgsz=engine.imgsz,
        ))
        print(f"{image_path.name}: 검출 {len(detections)}개, 추론 {elapsed:.3f}초 → {saved_path}")

    results_path = output_dir / "inference_results.csv"
    write_results(rows, results_path)
    print(f"결과 기록: {results_path}")


if __name__ == "__main__":
    main()
