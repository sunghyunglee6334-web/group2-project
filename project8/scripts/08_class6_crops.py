"""
08_class6_crops.py — 파·고추(Class 6) 박스만 잘라 한 장에 모음 (사람이 조각을 비교하는 QA용, Split은 바꾸지 않음)

실행 (project8 폴더에서):
    python scripts/08_class6_crops.py
    python scripts/08_class6_crops.py --group T00 --size 120

입력 : manifests/split_manifest.csv, data/final/images, data/final/labels
출력 : reports/class6_crops_<묶음>.jpg   사진 한 장 = 한 줄 (왼쪽: 순번·파일명·축소 사진, 오른쪽: 박스 조각)

보는 법
  1. 줄마다 파인지 고추인지 표시
  2. 파끼리, 고추끼리 조각 모양·길이·색·자른 면이 같은지 비교 → 같은 조각이면 같은 이름(A, B…)
  3. 앞에서 한 번도 안 나온 조각만 나오는 구간이 있으면 그 구간은 나눠도 누수 없음
"""
from pathlib import Path
import argparse

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLASS = "6"


def _font(size):
    for f in ["malgun.ttf", "C:/Windows/Fonts/malgun.ttf", "/mnt/c/Windows/Fonts/malgun.ttf",
              "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
              "/System/Library/Fonts/AppleSDGothicNeo.ttc", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit(im, S):
    """S×S 칸에 맞게 키우거나 줄임 (작은 조각도 크게 보이게)"""
    k = S / max(im.size)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)


def boxes(lbl: Path, cls: str):
    out = []
    if lbl and lbl.exists():
        for line in lbl.read_text(encoding="utf-8").splitlines():
            p = line.split()
            if len(p) >= 5 and p[0] == cls:
                out.append(tuple(map(float, p[1:5])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=PROJECT_ROOT / "manifests" / "split_manifest.csv")
    ap.add_argument("--data", default=PROJECT_ROOT / "data" / "final")
    ap.add_argument("--group", default=None, help="기본: Class 6 박스가 가장 많은 묶음")
    ap.add_argument("--size", type=int, default=110, help="조각 한 칸 크기(px)")
    ap.add_argument("--pad", type=float, default=0.15, help="박스 둘레 여백 비율")
    a = ap.parse_args()

    df = pd.read_csv(a.manifest, encoding="utf-8-sig")
    data = Path(a.data)
    imgs = {p.name: p for p in data.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}}
    lbls = {p.stem: p for p in data.rglob("*.txt")}
    df["_b"] = [boxes(lbls.get(Path(n).stem), CLASS) for n in df["image_name"]]
    g = a.group or df.assign(n=df["_b"].map(len)).groupby("time_group")["n"].sum().idxmax()
    t = df[df["time_group"] == g].sort_values("capture_time").reset_index(drop=True)

    S, info_w = a.size, a.size * 2 + 230
    ncol = max(1, max(len(b) for b in t["_b"]))
    W, H = info_w + ncol * (S + 6) + 10, (S + 8) * len(t) + 50
    sheet = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(sheet)
    f, fs = _font(18), _font(14)
    d.text((10, 12), f"{g} · Class 6 조각 모음 · {len(t)}장 (시간순)", fill="black", font=f)
    for i, r in t.iterrows():
        y = 50 + i * (S + 8)
        im = Image.open(imgs[r["image_name"]]).convert("RGB")
        w, h = im.size
        thumb = im.copy()
        td = ImageDraw.Draw(thumb)
        for k, (cx, cy, bw, bh) in enumerate(sorted(r["_b"])):     # 축소 사진에 박스 위치·번호 표시
            td.rectangle(((cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h),
                         outline="red", width=max(2, w // 300))
        thumb.thumbnail((S * 2, S))
        sheet.paste(thumb, (230, y))
        d.text((10, y + 4), f"{i + 1:02d}  ({len(r['_b'])}개)", fill="black", font=f)
        d.text((10, y + 32), r["image_name"], fill="#555", font=fs)
        d.text((10, y + 52), str(r["capture_time"])[11:19], fill="#555", font=fs)
        for k, (cx, cy, bw, bh) in enumerate(sorted(r["_b"])):     # 왼쪽 → 오른쪽 순서
            px, py = bw * w * a.pad, bh * h * a.pad
            box = (max(0, (cx - bw / 2) * w - px), max(0, (cy - bh / 2) * h - py),
                   min(w, (cx + bw / 2) * w + px), min(h, (cy + bh / 2) * h + py))
            crop = fit(im.crop(tuple(map(int, box))), S)
            x = info_w + k * (S + 6)
            sheet.paste(crop, (x + (S - crop.width) // 2, y + (S - crop.height) // 2))
            d.rectangle((x, y, x + S, y + S), outline="#ccc")
        d.line((0, y + S + 4, W, y + S + 4), fill="#eee")

    out = PROJECT_ROOT / "reports" / f"class6_crops_{g}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    print(f"저장: {out}  ({W}×{H}px, {len(t)}줄)")


if __name__ == "__main__":
    main()
