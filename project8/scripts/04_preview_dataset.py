"""3일차: Split 결과 라벨이 이미지에 제대로 붙었는지 눈으로 확인한다.
실행: python scripts/04_preview_dataset.py --split val --n 10"""

import argparse
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.label_visualizer import visualize

DATA_YAML = PROJECT_ROOT / "configs" / "dataset.yaml"
YOLO_DIR = PROJECT_ROOT / "data" / "yolo"
OUT_DIR = PROJECT_ROOT / "runs" / "preview"
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def load_class_names(yaml_path):
    """dataset.yaml 의 names 를 {번호: 이름} 으로 읽는다 (목록이든 dict 든)."""
    with open(yaml_path, encoding="utf-8") as f:
        names = yaml.safe_load(f)["names"]
    if isinstance(names, list):
        names = dict(enumerate(names))
    return {int(k): v for k, v in names.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="val", choices=["train", "val", "test"])
    parser.add_argument("--n", type=int, default=10, help="볼 이미지 수")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # 3일차 Split 이 끝나야 생기는 것들을 먼저 확인
    image_dir = YOLO_DIR / "images" / args.split
    label_dir = YOLO_DIR / "labels" / args.split
    for need in (DATA_YAML, image_dir, label_dir):
        if not need.exists():
            sys.exit(f"아직 없습니다: {need.relative_to(PROJECT_ROOT)}\n"
                     "→ 3일차 Split(② Data/QA) 이 끝난 뒤 다시 실행하세요.")

    class_names = load_class_names(DATA_YAML)

    images = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    random.Random(args.seed).shuffle(images)
    picked = images[: args.n]
    print(f"{args.split}: 전체 {len(images)}장 중 {len(picked)}장 확인")

    missing = 0
    for img in picked:
        txt = label_dir / f"{img.stem}.txt"
        if not txt.is_file():
            print("  라벨 없음:", txt.name)
            missing += 1
            continue
        out = visualize(img, txt, OUT_DIR / args.split / f"{img.stem}_gt.jpg", class_names)
        print("  저장:", out.relative_to(PROJECT_ROOT))
    print(f"완료. 라벨 없는 이미지 {missing}장. 결과 폴더: {(OUT_DIR / args.split).relative_to(PROJECT_ROOT)}")
    

if __name__ == "__main__":
    main()