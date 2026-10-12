"""연습/테스트용 가짜 데이터 생성기.

실제 NDA 데이터 없이도 프로그램을 개발·시험할 수 있도록
실제와 같은 폴더 구조(Dataset1/2, train/validation)와 일부러 넣은 오류를 만든다.

    python scripts/make_dummy_data.py              -> data/dummy_raw 에 생성
    python scripts/make_dummy_data.py --out D:/tmp/raw --n1 30
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

def background(w: int, h: int, kind: str, rng: np.random.Generator) -> Image.Image:
    """김치처럼 보이는 배경 (배추 조각 + 양념 + 고춧가루). object_only 는 밝은 단색 배경."""
    if kind == "object_only":
        g = np.linspace(225, 245, h, dtype=np.float32)[:, None, None]
        base = np.repeat(np.repeat(g, w // 8, 1), 3, 2) + rng.normal(0, 2, (h, w // 8, 3))
        return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((w, h))
    small = np.stack([rng.integers(150, 200, (h // 16, w // 16)), rng.integers(40, 75, (h // 16, w // 16)),
                      rng.integers(25, 50, (h // 16, w // 16))], -1).astype(np.uint8)
    im = Image.fromarray(small).resize((w, h), Image.BILINEAR)
    d = ImageDraw.Draw(im)
    s = w / 1920
    for _ in range(int(170)):                     # 배추 조각
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        r = rng.integers(int(60 * s), int(160 * s))
        ang = np.sort(rng.uniform(0, 2 * np.pi, rng.integers(5, 9)))
        pts = [(cx + r * rng.uniform(0.5, 1.1) * np.cos(a), cy + r * rng.uniform(0.35, 0.8) * np.sin(a)) for a in ang]
        base = rng.integers(205, 245)
        d.polygon(pts, fill=(int(base), int(base - rng.integers(5, 30)), int(base - rng.integers(50, 90))),
                  outline=(200, 110, 80))
        if rng.random() < 0.6:                        # 양념 묻은 부분
            d.line(pts[:3], fill=(190, 60, 40), width=max(2, int(6 * s)))
    for _ in range(int(2500 * s)):               # 고춧가루
        x, y = rng.integers(0, w), rng.integers(0, h)
        r = rng.integers(1, max(2, int(4 * s)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(170, 25, 20))
    return im


def draw_object(d: ImageDraw.ImageDraw, cls: int, w: int, h: int, rng: random.Random) -> tuple:
    """Class 별 이물 모양을 그리고, 그린 영역에 딱 맞는 YOLO 좌표를 돌려준다."""
    s = w / 1920
    bw = int(rng.randint(60, 220) * s)
    bh = int(rng.randint(40, 160) * s)
    x1 = rng.randint(0, w - bw - 1)
    y1 = rng.randint(0, h - bh - 1)
    x2, y2 = x1 + bw, y1 + bh
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    if cls == 0:            # 나뭇잎·종이: 초록 잎 / 흰 종이
        if rng.random() < 0.5:
            d.polygon([(x1, cy), (cx, y1), (x2, cy), (cx, y2)], fill=(70, 140, 50), outline=(40, 90, 30))
            d.line([(x1, cy), (x2, cy)], fill=(40, 90, 30), width=max(1, int(3 * s)))
        else:
            d.polygon([(x1, y1 + bh * 0.2), (x2 - bw * 0.1, y1), (x2, y2 - bh * 0.2), (x1 + bw * 0.1, y2)],
                      fill=(248, 248, 240), outline=(180, 180, 170))
    elif cls == 1:          # 플라스틱·돌·금속
        kind = rng.choice(["plastic", "stone", "metal"])
        if kind == "plastic":
            d.polygon([(x1, y1 + bh * 0.3), (cx, y1), (x2, y1 + bh * 0.4), (x2 - bw * 0.2, y2), (x1 + bw * 0.1, y2)],
                      fill=(170, 210, 235), outline=(90, 140, 190))
        elif kind == "stone":
            d.ellipse([x1, y1, x2, y2], fill=(120, 118, 112), outline=(70, 70, 65))
        else:
            d.rectangle([x1, y1, x2, y2], fill=(185, 190, 195), outline=(110, 115, 120), width=max(1, int(3 * s)))
    elif cls == 2:          # 나뭇가지
        t = max(3, int(10 * s))
        d.line([(x1, y2), (x2, y1)], fill=(105, 70, 35), width=t)
        d.line([(cx, cy), (cx + bw * 0.3, y2)], fill=(105, 70, 35), width=max(2, t // 2))
    elif cls == 3:          # 벌레
        m = max(4, int(min(bw, bh) * 0.25))
        d.ellipse([x1 + m, y1 + m, x2 - m, y2 - m], fill=(25, 25, 25))
        for k in range(3):
            yy = y1 + m + (bh - 2 * m) * (k + 1) / 4
            d.line([(x1, yy - m / 2), (x2, yy + m / 2)], fill=(25, 25, 25), width=max(1, int(3 * s)))
    elif cls == 5:          # 병해·갈변
        d.ellipse([x1, y1, x2, y2], fill=(110, 70, 30))
        d.ellipse([x1 + bw * 0.2, y1 + bh * 0.2, x2 - bw * 0.2, y2 - bh * 0.2], fill=(80, 45, 20))
    else:                   # 6 파·고추
        if rng.random() < 0.5:
            d.rounded_rectangle([x1, y1, x2, y2], radius=int(min(bw, bh) / 2), fill=(90, 170, 60), outline=(50, 110, 30))
        else:
            d.rounded_rectangle([x1, y1, x2, y2], radius=int(min(bw, bh) / 2), fill=(200, 30, 25), outline=(130, 15, 10))
    return cls, cx / w, cy / h, bw / w, bh / h


def make_split(root: Path, dataset: str, split: str, n: int, rng: random.Random,
               nrng: np.random.Generator, big_every: int = 5) -> list[Path]:
    img_dir = root / dataset / "images" / split
    lbl_dir = root / dataset / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for i in range(n):
        w, h = (3840, 2160) if i % big_every == 0 else (1920, 1080)
        kind = rng.choice(["kimchi_with_target"] * 3 + ["normal_kimchi", "object_only"])
        im = background(w, h, kind, nrng)
        d = ImageDraw.Draw(im)
        lines = []
        if kind != "normal_kimchi":
            for _ in range(rng.randint(1, 4 if kind == "kimchi_with_target" else 1)):
                cls = rng.choice([0, 1, 2, 3, 5, 6])
                lines.append("%d %.6f %.6f %.6f %.6f" % draw_object(d, cls, w, h, rng))
        name = f"{dataset[-1]}_{split}_{i:04d}"
        im.save(img_dir / f"{name}.jpg", quality=85)
        (lbl_dir / f"{name}.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        made.append(lbl_dir / f"{name}.txt")
    return made


def inject_errors(root: Path, labels: list[Path], rng: random.Random) -> list[str]:
    """의도적 오류 (Validation 이 찾아야 하는 것들)."""
    log = []
    candidates = [p for p in labels if p.read_text().strip()]
    rng.shuffle(candidates)
    p = candidates.pop(); p.unlink(); log.append(f"TXT 삭제(PAIR_NO_TXT): {p.name}")
    p = candidates.pop()
    p.write_text(p.read_text().replace(p.read_text().split()[0], "4", 1)); log.append(f"Class 4: {p.name}")
    p = candidates.pop(); p.write_text(p.read_text() + "2 1.200000 0.5 0.1 0.1\n"); log.append(f"좌표 범위 오류: {p.name}")
    p = candidates.pop(); p.write_text(p.read_text() + "3 0.5 0.5\n"); log.append(f"줄 구조 오류: {p.name}")
    p = candidates.pop(); p.write_text(p.read_text() + "9 0.5 0.5 0.1 0.1\n"); log.append(f"Class 범위 오류: {p.name}")
    p = candidates.pop(); first = p.read_text().splitlines()[0]
    p.write_text(p.read_text() + first + "\n"); log.append(f"중복 BBox: {p.name}")
    orphan = labels[0].parent / "orphan_without_image.txt"
    orphan.write_text("1 0.5 0.5 0.1 0.1\n"); log.append(f"짝 없는 TXT(PAIR_NO_JPG): {orphan.name}")
    return log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "dummy_raw"))
    ap.add_argument("--n1", type=int, default=24, help="Dataset1/train 수")
    ap.add_argument("--n2", type=int, default=18, help="Dataset2/train 수")
    ap.add_argument("--n2v", type=int, default=10, help="Dataset2/validation 수")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} 가 비어있지 않습니다. 다른 경로를 쓰거나 지우고 다시 실행하세요.")
    rng, nrng = random.Random(args.seed), np.random.default_rng(args.seed)
    labels = []
    labels += make_split(out, "이물검출_학습데이터1", "train", args.n1, rng, nrng)
    labels += make_split(out, "이물검출_학습데이터2", "train", args.n2, rng, nrng)
    labels += make_split(out, "이물검출_학습데이터2", "validation", args.n2v, rng, nrng)
    for line in inject_errors(out, labels, rng):
        print(" -", line)
    print(f"완료: {out}  (이미지 {args.n1 + args.n2 + args.n2v}장)")


if __name__ == "__main__":
    main()
