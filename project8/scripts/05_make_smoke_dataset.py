"""Smoke Dataset 만들기 (03_build_split.py 를 COPY_IMAGES = True 로 실행한 다음)

data/yolo 의 train · val 에서 이름순 앞쪽 일부만 data/smoke 로 복사하고
configs/smoke_dataset.yaml 을 만든다. test · bridge 는 읽지 않는다.

    python scripts/05_make_smoke_dataset.py
"""
import shutil
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_check import list_images  # noqa: E402
from src.project_config import CLASS_NAMES, SMOKE_DIR, SMOKE_YAML, YOLO_DIR  # noqa: E402

N_TRAIN = 30
N_VAL = 8


def copy_split(split, n):
    img_dir = YOLO_DIR / "images" / split
    lbl_dir = YOLO_DIR / "labels" / split
    if not img_dir.is_dir() or not lbl_dir.is_dir():
        print(f"{img_dir} 가 없습니다. scripts/03_build_split.py 를 COPY_IMAGES = True 로 먼저 실행하세요.")
        raise SystemExit(1)

    images = list_images(img_dir)[:n]
    if len(images) < n:
        print(f"{img_dir} 이미지가 {len(images)}장뿐입니다 ({n}장 필요)")
        raise SystemExit(1)

    out_img = SMOKE_DIR / "images" / split
    out_lbl = SMOKE_DIR / "labels" / split
    out_img.mkdir(parents=True)
    out_lbl.mkdir(parents=True)
    for img in images:
        lbl = lbl_dir / f"{img.stem}.txt"
        if not lbl.exists():
            print(f"{img.name} 짝 TXT 없음 ({lbl_dir})")
            raise SystemExit(1)
        shutil.copy2(img, out_img / img.name)
        shutil.copy2(lbl, out_lbl / lbl.name)
    print(f"[{split}] {len(images)}쌍 -> {out_img.relative_to(PROJECT_ROOT)}")
    return len(images)


def write_yaml():
    data = {
        "path": str(SMOKE_DIR),
        "train": "images/train",
        "val": "images/val",
        "names": CLASS_NAMES,
    }
    SMOKE_YAML.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_YAML.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"YAML -> {SMOKE_YAML.relative_to(PROJECT_ROOT)}")


def main():
    # data/smoke 는 이 스크립트가 만드는 파생 폴더라 매번 새로 만든다
    if SMOKE_DIR.exists():
        shutil.rmtree(SMOKE_DIR)
    n_train = copy_split("train", N_TRAIN)
    n_val = copy_split("val", N_VAL)
    write_yaml()
    print(f"완료: Train {n_train} / Val {n_val}")


if __name__ == "__main__":
    main()
