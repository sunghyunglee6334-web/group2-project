"""Final 모델 검출을 교과 8 시연용 후보 YOLO 라벨로 저장한다.

후보 TXT는 교과 8 demo/auto_label/candidate_labels에 저장한다.
검수 전에는 정답 라벨로 취급하지 않는다. Human Review는 이 모듈과 분리되어 있다.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .project_config import CLASS_NAMES, IMG_EXTS, MODEL_DIR, PROJECT_ROOT

if TYPE_CHECKING:
    from .inference import Detection, ImageInference

PROJECT7_ROOT = PROJECT_ROOT.parent / "project7"
CANDIDATE_DIR = PROJECT_ROOT / "demo" / "auto_label" / "candidate_labels"
CLASSES_FILE = PROJECT7_ROOT / "configs" / "classes.yaml"


@dataclass(frozen=True)
class AutoLabelResult:
    """후보 TXT 저장 결과."""

    ok: bool
    label_path: Path | None
    message: str
    count: int = 0


def _active_class_ids() -> set[int]:
    """교과 7 Class 설정에서 새 BBox 생성이 허용된 ID를 읽는다."""
    if not CLASSES_FILE.is_file():
        raise FileNotFoundError(f"교과 7 Class 설정 파일이 없습니다: {CLASSES_FILE}")
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML이 필요합니다. project7의 requirements.txt를 설치하세요.") from exc

    data = yaml.safe_load(CLASSES_FILE.read_text(encoding="utf-8")) or {}
    classes = data.get("classes") or {}
    active = {int(cid) for cid, info in classes.items() if info.get("enabled", True)}
    if not active:
        raise ValueError(f"활성 Class가 없습니다: {CLASSES_FILE}")
    return active


def candidate_label_path(image_path: str | Path, out_dir: str | Path | None = None) -> Path:
    """이미지 stem에 대응하는 교과 8 후보 라벨 경로를 반환한다."""
    image = Path(image_path).expanduser()
    return Path(out_dir).expanduser() / f"{image.stem}.txt" if out_dir else CANDIDATE_DIR / f"{image.stem}.txt"


def _serialize(detections: list[Detection], width: int, height: int,
               active_ids: set[int]) -> tuple[str, int]:
    if width <= 0 or height <= 0:
        raise ValueError(f"이미지 크기가 올바르지 않습니다: {width}x{height}")

    lines: list[str] = []
    for detection in detections:
        class_id = detection.class_id
        if class_id not in active_ids or class_id not in CLASS_NAMES:
            continue
        x1, y1, x2, y2 = detection.bbox_xyxy
        x1, x2 = sorted((max(0.0, min(float(x1), width)), max(0.0, min(float(x2), width))))
        y1, y2 = sorted((max(0.0, min(float(y1), height)), max(0.0, min(float(y2), height))))
        box_width, box_height = x2 - x1, y2 - y1
        if box_width <= 0 or box_height <= 0:
            continue
        cx, cy = (x1 + x2) / 2 / width, (y1 + y2) / 2 / height
        lines.append(f"{class_id} {cx:.6f} {cy:.6f} {box_width / width:.6f} {box_height / height:.6f}")
    return ("\n".join(lines) + ("\n" if lines else ""), len(lines))


def _write_file(path: Path, text: str, overwrite: bool) -> None:
    """overwrite가 False면 배타 생성, True면 임시파일 교체로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        except FileExistsError:
            raise FileExistsError(f"후보 라벨이 이미 있습니다: {path}") from None
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        return

    fd, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temp_name, path)
    except FileExistsError:
        raise FileExistsError(f"후보 라벨이 이미 있습니다: {path}") from None
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def run_auto_label(
    image_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    overwrite: bool = False,
    inference: ImageInference | None = None,
) -> AutoLabelResult:
    """이미지 한 장을 추론해 후보 YOLO TXT를 저장한다.

    기존 후보는 기본적으로 보호한다. 사용자가 기존 파일 확인 후 명시적으로
    ``overwrite=True``를 전달한 경우에만 교체한다.
    """
    image = Path(image_path).expanduser()
    if not image.is_file():
        raise FileNotFoundError(f"입력 이미지가 없습니다: {image}")
    if image.suffix.lower() not in IMG_EXTS:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {image.suffix}")

    output = candidate_label_path(image, output_dir)
    if output.exists() and not overwrite:
        return AutoLabelResult(False, output, f"후보 라벨이 이미 있습니다: {output.name}")

    from PIL import Image

    with Image.open(image) as source:
        width, height = source.size
    if inference is None:
        from .inference import FINAL_IMGSZ, ImageInference

        engine = ImageInference(weight_path=MODEL_DIR / "final" / "final_best.pt", imgsz=FINAL_IMGSZ)
    else:
        engine = inference
    detections = engine.predict(image)
    text, count = _serialize(detections, width, height, _active_class_ids())
    try:
        _write_file(output, text, overwrite)
    except OSError as exc:
        return AutoLabelResult(False, output, f"후보 라벨 저장 실패: {exc}")
    message = f"후보 라벨 저장: {output.name} ({count}개)"
    return AutoLabelResult(True, output, message, count)
