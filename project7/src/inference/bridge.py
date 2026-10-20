"""GUI <-> 추론(Detection) · Auto Label 기능 코드 연결 지점.

GUI 는 이 파일의 함수만 부른다. 모델을 불러오고 예측하는 코드는 GUI 안에 만들지 않는다.
지금은 기능 코드(추론 담당)가 준비 중이라 **더미(가짜 결과)** 로 동작한다.

    run_detection(image_path)                     -> list[Detection]
    run_auto_label(image_path, detections, ...)   -> AutoLabelResult

[연결 방법] 추론 담당 함수가 준비되면 아래 두 함수 안의 '더미' 부분만 실제 호출로 바꾼다.
    예) from <추론 모듈> import detect          # 실제 모듈 · 함수 이름은 협의 후 결정
        return [Detection(c, conf, *xyxy) for c, conf, xyxy in detect(image_path)]
반환 형식(Detection, AutoLabelResult)만 지키면 GUI 는 고칠 필요가 없다.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ..config import ACTIVE_CLASS_IDS, CLASS_NAMES, PROJECT_ROOT
from ..yolo.yolo_io import Box, atomic_write_text, boxes_to_text

# 화면에 보여 줄 모델 정보 (교과 8 Final Model 기준)
MODEL_INFO = {
    "connected": False,                         # 실제 기능 코드와 연결되면 True
    "weight": "models/final/final_best.pt",
    "imgsz": 1280,
    "conf": 0.25,
}

# AI 가 만든 후보 라벨 저장 위치 (사람이 검수한 저장본은 기존 WORK 폴더에 따로 저장된다)
CANDIDATE_DIR = PROJECT_ROOT / "data" / "auto_label" / "candidate_labels"

# 시연에 임의로 쓰면 안 되는 데이터 (Frozen Test · Bridge Holdout)
BLOCKED_DIRS = ("fr_test", "frozen_test", "bridge_holdout")


@dataclass
class Detection:
    """검출 결과 1개. 좌표는 원본 이미지 픽셀 (x1, y1, x2, y2)."""
    class_id: int
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def xyxy(self) -> tuple[float, float, float, float]:
        return self.x1, self.y1, self.x2, self.y2

    @property
    def class_name(self) -> str:
        return CLASS_NAMES.get(self.class_id, "범위 밖")


@dataclass
class AutoLabelResult:
    ok: bool
    label_path: Path | None
    message: str
    count: int = 0


def check_demo_allowed(image_path: str | Path) -> str | None:
    """시연에 쓰면 안 되는 이미지면 이유를, 괜찮으면 None 을 돌려준다."""
    parts = [p.lower() for p in Path(image_path).parts]
    for name in BLOCKED_DIRS:
        if name in parts:
            return f"'{name}' 폴더 이미지는 시연용으로 쓰지 않습니다 (Frozen Test · Bridge Holdout 보호)."
    return None


def candidate_label_path(image_path: str | Path, out_dir: str | Path | None = None) -> Path:
    return Path(out_dir or CANDIDATE_DIR) / f"{Path(image_path).stem}.txt"


# ==================================================================== Detection
def run_detection(image_path: str | Path) -> list[Detection]:
    """입력: 이미지 경로 / 출력: 검출 목록 (클래스 ID · Confidence · 픽셀 좌표).

    TODO(추론 담당 연결): 아래 더미를 실제 추론 함수 호출로 교체.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"이미지가 없습니다: {path}")
    return _dummy_detection(path)


def _dummy_detection(path: Path) -> list[Detection]:
    """더미: 파일 이름으로 시드를 정해 매번 같은 가짜 박스 2~4개를 만든다."""
    time.sleep(0.8)                              # 로딩 표시 확인용
    with Image.open(path) as im:
        w, h = im.size
    rng = random.Random(path.name)
    out = []
    for _ in range(rng.randint(2, 4)):
        bw, bh = rng.uniform(0.05, 0.16) * w, rng.uniform(0.05, 0.16) * h
        x1, y1 = rng.uniform(0, w - bw), rng.uniform(0, h - bh)
        out.append(Detection(rng.choice(ACTIVE_CLASS_IDS), round(rng.uniform(0.3, 0.95), 2),
                             x1, y1, x1 + bw, y1 + bh))
    return sorted(out, key=lambda d: -d.conf)


# ==================================================================== Auto Label
def run_auto_label(image_path: str | Path, detections: list[Detection],
                   out_dir: str | Path | None = None, overwrite: bool = False) -> AutoLabelResult:
    """입력: 이미지 경로 + 검출 결과 / 출력: 저장된 후보 라벨 경로 + 처리 결과.

    TODO(추론 담당 연결): 실제 라벨 생성 함수가 있으면 그 함수로 교체.
    """
    path = Path(image_path)
    out = candidate_label_path(path, out_dir)
    if out.exists() and not overwrite:
        return AutoLabelResult(False, out, f"후보 라벨이 이미 있습니다: {out.name}")

    with Image.open(path) as im:
        w, h = im.size
    boxes = [Box(d.class_id, *d.xyxy).clamp(w, h) for d in detections if d.class_id in ACTIVE_CLASS_IDS]
    try:
        atomic_write_text(out, boxes_to_text(boxes, w, h))
    except OSError as e:
        return AutoLabelResult(False, out, f"저장 실패: {e}")
    return AutoLabelResult(True, out, f"후보 라벨 저장: {out.name} ({len(boxes)}개)", len(boxes))
