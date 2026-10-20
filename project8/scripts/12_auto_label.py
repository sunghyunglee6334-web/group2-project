"""Final Model로 시연 이미지를 추론하고 후보 YOLO TXT를 저장한다.

실행 (project8 폴더에서):
    python scripts/12_auto_label.py
    python scripts/12_auto_label.py --input data/test_detection/sample.jpg

후보 라벨 기본 저장 위치:
    demo/auto_label/candidate_labels/
실행 결과 기록:
    demo/auto_label/candidate_labels/auto_label_results.csv
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

from src.auto_label import CANDIDATE_DIR, run_auto_label  # noqa: E402
from src.auto_label_review import register_candidates  # noqa: E402
from src.inference import FINAL_IMGSZ, FINAL_WEIGHT, ImageInference  # noqa: E402
from src.project_config import IMG_EXTS, PRED_CONF  # noqa: E402

DEFAULT_RESULTS = CANDIDATE_DIR / "auto_label_results.csv"
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "test_detection"
BLOCKED_PATH_PARTS = {"train", "val", "validation", "test", "fr_test", "frozen_test", "bridge_holdout"}
RESULT_COLUMNS = [
    "input_image", "candidate_label", "status", "detection_count", "elapsed_seconds",
    "model_weight", "confidence_threshold", "imgsz", "message",
]


def collect_images(input_path: Path) -> list[Path]:
    """이미지 한 장 또는 폴더 바로 아래의 이미지를 반환한다."""
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
        raise FileNotFoundError(f"입력 폴더 바로 아래에 지원되는 이미지가 없습니다: {input_path}")
    return images


def validate_input_scope(images: list[Path]) -> None:
    """학습·평가·Bridge split은 막고, 전용 test_detection 시연 폴더는 허용한다."""
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
            raise ValueError(f"분할 데이터({names})는 Auto Label 입력으로 사용할 수 없습니다: {image}")


def write_results(rows: list[dict[str, object]], output_path: Path) -> None:
    """이미지마다 한 행의 실행 결과를 UTF-8 BOM CSV로 남긴다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def report_path(path: Path) -> str:
    """결과 CSV에는 프로젝트 기준 경로를 쓰고, 외부 경로는 파일명만 남긴다."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT.parent).as_posix()
    except ValueError:
        return path.name


def main() -> int:
    parser = argparse.ArgumentParser(description="Final Model로 후보 YOLO 라벨을 생성합니다.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_DIR,
                        help="시연 이미지 한 장 또는 폴더 (기본: data/test_detection)")
    parser.add_argument("--output-dir", type=Path, default=CANDIDATE_DIR,
                        help="후보 TXT 저장 폴더 (기본: demo/auto_label/candidate_labels)")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS,
                        help="처리 결과 CSV 경로")
    parser.add_argument("--conf", type=float, default=PRED_CONF,
                        help=f"검출 Confidence 기준 (기본: {PRED_CONF})")
    parser.add_argument("--imgsz", type=int, default=FINAL_IMGSZ,
                        help=f"추론 입력 크기 (기본: {FINAL_IMGSZ})")
    parser.add_argument("--overwrite", action="store_true",
                        help="기존 후보 TXT를 명시적으로 덮어씀")
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    results_path = args.results.expanduser().resolve()
    if not 0.0 <= args.conf <= 1.0:
        parser.error("--conf는 0부터 1 사이여야 합니다.")
    if args.imgsz <= 0:
        parser.error("--imgsz는 양수여야 합니다.")

    try:
        images = collect_images(input_path)
        validate_input_scope(images)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    # 후보 TXT는 stem으로 저장하므로, 폴더 안에 같은 stem이 있으면 먼저 중단한다.
    seen_stems: set[str] = set()
    duplicates: set[str] = set()
    for image in images:
        stem = image.stem.casefold()
        if stem in seen_stems:
            duplicates.add(stem)
        seen_stems.add(stem)
    if duplicates:
        parser.error("같은 파일명이 있어 후보 TXT 경로가 겹칩니다: " + ", ".join(sorted(duplicates)))

    output_paths = [output_dir / f"{image.stem}.txt" for image in images]
    if results_path in set(output_paths):
        parser.error("결과 CSV 경로가 후보 TXT 경로와 겹칩니다.")

    rows: list[dict[str, object]] = []
    try:
        if not FINAL_WEIGHT.is_file():
            raise FileNotFoundError(f"최종 모델 Weight 파일이 없습니다: {FINAL_WEIGHT}")
        engine = ImageInference(weight_path=FINAL_WEIGHT, imgsz=args.imgsz, conf=args.conf)
    except Exception as exc:
        message = f"모델을 불러오지 못했습니다: {exc}"
        for image, label_path in zip(images, output_paths):
            rows.append({
                "input_image": image.name, "candidate_label": report_path(label_path), "status": "ERROR",
                "detection_count": "", "elapsed_seconds": "", "model_weight": report_path(FINAL_WEIGHT),
                "confidence_threshold": args.conf, "imgsz": args.imgsz, "message": message,
            })
        write_results(rows, results_path)
        print(message)
        print(f"결과 기록: {results_path}")
        return 1

    errors = 0
    for image in images:
        started = time.perf_counter()
        try:
            result = run_auto_label(
                image,
                output_dir=output_dir,
                overwrite=args.overwrite,
                inference=engine,
            )
            elapsed = time.perf_counter() - started
            status = "OK" if result.ok else "SKIPPED"
            errors += int(not result.ok)
            label_path = result.label_path or output_dir / f"{image.stem}.txt"
            count: int | str = result.count if result.ok else ""
            message = result.message
        except Exception as exc:
            elapsed = time.perf_counter() - started
            status, count = "ERROR", ""
            label_path = output_dir / f"{image.stem}.txt"
            message = f"{type(exc).__name__}: {exc}"
            errors += 1

        rows.append({
            "input_image": image.name,
            "candidate_label": report_path(label_path),
            "status": status,
            "detection_count": count,
            "elapsed_seconds": round(elapsed, 6),
            "model_weight": report_path(engine.weight_path),
            "confidence_threshold": engine.conf,
            "imgsz": engine.imgsz,
            "message": message,
        })
        print(f"{image.name}: {status} · {message}")

    write_results(rows, results_path)
    review_results_path = PROJECT_ROOT / "reports" / "auto_label_review.csv"
    register_candidates(review_results_path, rows)
    print(f"처리 {len(images)}장 · 오류/건너뜀 {errors}건")
    print(f"결과 기록: {results_path}")
    print(f"Human Review 추적: {review_results_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
