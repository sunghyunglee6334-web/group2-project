"""프로젝트 공통 설정.

모든 경로는 여기서만 만든다. (경로 하드코딩 금지)
PC마다 다른 값(raw 데이터 위치, 작업자 이름)은 프로젝트 루트의
settings.json 에 적는다. settings.json 은 Git 에 올리지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = PROJECT_ROOT / "settings.json"
EXAMPLE_SETTINGS_FILE = PROJECT_ROOT / "settings.example.json"
REPORT_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"
MANIFESTS_DIR = PROJECT_ROOT / "manifests"

# ---------------------------------------------------------------- Class 기준 (Freeze)
# Class 표는 configs/classes.yaml 한 곳에서 관리한다. 번호는 절대 다시 매기지 않는다.
# enabled: false 인 Class(4번 고무장갑)는 새 BBox 에 쓸 수 없고, 발견되면 REVIEW 대상이다.
CLASSES_FILE = PROJECT_ROOT / "configs" / "classes.yaml"
DEFAULT_COLOR = "#ff0000"


def load_classes(path: Path = CLASSES_FILE) -> dict[int, dict]:
    try:
        import yaml
    except ImportError as e:
        raise SystemExit("PyYAML 이 없습니다: pip install -r requirements.txt") from e
    if not path.exists():
        raise SystemExit(f"Class 설정 파일이 없습니다: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    classes = {}
    for cid, item in (data.get("classes") or {}).items():
        classes[int(cid)] = {
            "name": str(item["name"]),
            "enabled": bool(item.get("enabled", True)),
            "color": str(item.get("color", DEFAULT_COLOR)),
        }
    if not classes:
        raise SystemExit(f"{path} 에 classes 가 비어 있습니다.")
    return dict(sorted(classes.items()))


CLASSES = load_classes()
CLASS_NAMES: dict[int, str] = {cid: c["name"] for cid, c in CLASSES.items()}
CLASS_COLORS: dict[int, str] = {cid: c["color"] for cid, c in CLASSES.items()}
VALID_CLASS_IDS = set(CLASS_NAMES)                                    # 0~6 : 형식상 허용
UNUSED_CLASS_IDS = {cid for cid, c in CLASSES.items() if not c["enabled"]}   # {4}
ACTIVE_CLASS_IDS = sorted(VALID_CLASS_IDS - UNUSED_CLASS_IDS)

# ---------------------------------------------------------------- 작업 상태
STATUSES = ["PENDING", "WORKING", "PASS", "EDITED", "REVIEW", "REVIEWED", "FINAL"]
# FINAL 로 갈 수 있는 상태
FINAL_READY_STATUSES = {"PASS", "REVIEWED"}

SCENE_TYPES = ["", "kimchi_with_target", "normal_kimchi", "object_only", "other_review"]

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# BBox 기준
MIN_BOX_PX = 3.0            # 원본 픽셀 기준 이보다 작은 BBox 는 만들지 않음(실수 드래그 방지)
DUP_IOU_THRESHOLD = 0.9     # 같은 Class 이고 IoU 가 이보다 크면 중복 의심


def load_settings() -> dict:
    """settings.json 을 읽는다. 없으면 example 값을 사용한다."""
    data: dict = {}
    if EXAMPLE_SETTINGS_FILE.exists():
        data.update(json.loads(EXAMPLE_SETTINGS_FILE.read_text(encoding="utf-8")))
    if SETTINGS_FILE.exists():
        data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    return data


def save_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _abs(p: str) -> Path:
    path = Path(p).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path)


class Paths:
    """RAW / WORK / FINAL 경로 묶음."""

    def __init__(self, raw_root: str | Path | None = None, work_root: str | Path | None = None,
                 final_root: str | Path | None = None):
        s = load_settings()
        self.raw = _abs(str(raw_root)) if raw_root else _abs(s.get("raw_root", "data/raw"))
        self.work = _abs(str(work_root)) if work_root else _abs(s.get("work_root", "data/work"))
        self.final = _abs(str(final_root)) if final_root else _abs(s.get("final_root", "data/final"))

    @property
    def manifest(self) -> Path:
        return self.work / "manifest.csv"

    @property
    def work_labels(self) -> Path:
        return self.work / "labels"

    def check_not_same(self) -> None:
        """RAW 와 WORK 가 같은 폴더면 RAW 가 망가질 수 있으므로 즉시 중단."""
        raw, work = self.raw.resolve(), self.work.resolve()
        if raw == work or raw in work.parents or work in raw.parents:
            raise SystemExit(f"[중단] RAW({raw}) 와 WORK({work}) 는 서로 다른 독립 폴더여야 합니다.")
