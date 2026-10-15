"""
05_check_phash.py — Split 후 pHash로 '비슷한 사진'이 split을 넘나드는지 확인 (배정은 바꾸지 않음)

실행 (project8 폴더에서, 03_build_split.py 다음에):
    python scripts/05_check_phash.py           확인만 (imagehash 설치 없이 동작 — 같은 pHash 계산을 numpy로 직접 함)
    python scripts/05_check_phash.py --apply   거리 ≤ 5(거의 같음)인 평가 쪽 사진을 manifests에 eval_exclude=True로 표시

입력 : manifests/split_manifest.csv, data/final/images
출력 : reports/phash_check.csv (비슷한 사진 쌍 목록), 화면 요약

확인하는 것
  [A] 묶음 경계: 앞 묶음 끝 K장 ↔ 다음 묶음 첫 K장의 가장 가까운 거리
      → 다른 split으로 갈라진 경계가 비슷하면 누수 의심
  [B] split 사이 전체: 서로 다른 split의 모든 사진 쌍 중 거리가 SIMILAR 이하인 쌍
  [C] T17_V(Val 이물만 15장) ↔ T17 나머지(Train): 같은 이물이라 가까운 게 정상 → 얼마나 가까운지 기록

pHash 거리 (64비트 중 다른 비트 수)
  0~5   거의 같은 사진 (같은 장면)
  6~10  비슷한 사진 (확인 필요)
  11~   다른 사진
"""
from pathlib import Path
import argparse
import itertools
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAME, SIMILAR, K = 5, 10, 5        # 거의 같음 / 비슷함 기준, 경계에서 볼 장수


class PHash:
    """64비트 pHash. a - b = 서로 다른 비트 수 (imagehash.phash와 같은 방식)"""
    def __init__(self, bits):
        self.bits = bits

    def __sub__(self, other):
        return int((self.bits != other.bits).sum())


def _dct_matrix(n):
    import numpy as np
    k = np.arange(n)[:, None]
    m = np.cos(np.pi * (2 * np.arange(n)[None, :] + 1) * k / (2 * n))
    return m * 2                                   # scipy dct(type 2) 비례 (크기는 결과에 영향 없음)


def phash_all(paths):
    """회색 32×32로 줄임 → 2차원 DCT → 왼쪽 위 8×8(저주파) → 중앙값보다 크면 1"""
    import numpy as np
    from PIL import Image
    D = _dct_matrix(32)
    out = []
    for i, p in enumerate(paths, 1):
        with Image.open(p) as im:
            im.draft("L", (512, 512))          # JPEG를 작게 읽어 빠르게 (4K 원본 그대로 읽지 않음)
            g = np.asarray(im.convert("L").resize((32, 32), Image.LANCZOS), dtype=float)
        low = (D @ g @ D.T)[:8, :8]
        out.append(PHash((low > np.median(low)).flatten()))
        if i % 100 == 0:
            print(f"  … pHash {i}/{len(paths)}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=PROJECT_ROOT / "manifests" / "split_manifest.csv")
    ap.add_argument("--images", default=PROJECT_ROOT / "data" / "final")
    ap.add_argument("--out", default=PROJECT_ROOT / "reports" / "phash_check.csv")
    ap.add_argument("--apply", action="store_true", help="거리 ≤ 5인 평가 쪽 사진을 eval_exclude=True로 manifests에 기록")
    a = ap.parse_args()

    df = pd.read_csv(a.manifest, encoding="utf-8-sig")
    idx = {p.name: p for p in Path(a.images).rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}}
    df["_img"] = df["image_name"].map(idx)
    if df["_img"].isna().any():
        sys.exit(f"이미지를 찾지 못함: {df['_img'].isna().sum()}장 (--images 경로 확인)")
    df = df.sort_values("capture_time").reset_index(drop=True)
    print(f"pHash 계산 중 ({len(df)}장, 1~2분)…", flush=True)
    df["_h"] = phash_all(df["_img"])

    rows = []

    # [A] 묶음 경계
    print("\n[A] 묶음 경계 (앞 묶음 끝 5장 ↔ 다음 묶음 첫 5장)")
    tg = list(dict.fromkeys(df["time_group"]))
    for g1, g2 in zip(tg, tg[1:]):
        a1, a2 = df[df["time_group"] == g1].tail(K), df[df["time_group"] == g2].head(K)
        best = min(((x["_h"] - y["_h"], x, y) for _, x in a1.iterrows() for _, y in a2.iterrows()),
                   key=lambda z: z[0])
        d, x, y = best
        s1, s2 = x["split"], y["split"]
        flag = "⚠ 누수 의심" if s1 != s2 and d <= SIMILAR else ("같은 split" if s1 == s2 else "OK")
        print(f"  {g1}({s1}) ↔ {g2}({s2}) : 최소 거리 {d:2d}  {flag}")
        rows.append({"check": "A_boundary", "image_a": x["image_name"], "image_b": y["image_name"],
                     "group_a": g1, "group_b": g2, "split_a": s1, "split_b": s2, "distance": d, "flag": flag})

    # [B] 서로 다른 split의 모든 쌍
    print(f"\n[B] 서로 다른 split인데 거리 ≤ {SIMILAR}인 쌍")
    hs = list(zip(df.index, df["_h"], df["split"], df["group_id"]))
    found = []
    for (i, hi, si, gi), (j, hj, sj, gj) in itertools.combinations(hs, 2):
        if si != sj and not ({gi, gj} >= {"T17", "T17_V"}):     # T17_V ↔ T17은 [C]에서 따로
            d = hi - hj
            if d <= SIMILAR:
                found.append((d, i, j))
    for d, i, j in sorted(found):
        x, y = df.loc[i], df.loc[j]
        flag = "거의 같음" if d <= SAME else "비슷함"
        rows.append({"check": "B_cross_split", "image_a": x["image_name"], "image_b": y["image_name"],
                     "group_a": x["group_id"], "group_b": y["group_id"], "split_a": x["split"],
                     "split_b": y["split"], "distance": d, "flag": flag})
    pairs = pd.DataFrame([r for r in rows if r["check"] == "B_cross_split"])
    if pairs.empty:
        print("  없음 ✅")
    else:
        print(pairs.groupby(["split_a", "split_b", "flag"]).size().to_string())
        print("  (자세한 목록: reports/phash_check.csv)")

    # [C] T17_V ↔ T17
    v, t = df[df["group_id"] == "T17_V"], df[df["group_id"] == "T17"]
    if len(v) and len(t):
        dmin = []
        for i, h in zip(v.index, v["_h"]):
            d, j = min((h - ht, j) for j, ht in zip(t.index, t["_h"]))
            dmin.append(d)
            rows.append({"check": "C_T17V_vs_T17", "image_a": v.at[i, "image_name"], "image_b": t.at[j, "image_name"],
                         "group_a": "T17_V", "group_b": "T17", "split_a": v.at[i, "split"], "split_b": t.at[j, "split"],
                         "distance": d, "flag": "거의 같음" if d <= SAME else ("비슷함" if d <= SIMILAR else "다름")})
        print(f"\n[C] T17_V {len(v)}장 ↔ T17 나머지(Train): 최소 거리 중앙값 {int(pd.Series(dmin).median())}, "
              f"거의 같음(≤{SAME}) {sum(d <= SAME for d in dmin)}장")
        print("    → 같은 이물이라 가까운 게 정상. Val 이물만 점수는 참고용 (same_bundle_split=True)")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    risky = [r for r in rows
             if r["split_a"] != r["split_b"] and r["distance"] <= SIMILAR
             and ({"test", "bridge_holdout"} & {r["split_a"], r["split_b"]})]
    print(f"\n결론: Test·Bridge가 걸린 비슷한 쌍 {len(risky)}개"
          + (" → 없음, 경계 누수 걱정 없음 ✅" if not risky else " → reports/phash_check.csv 확인 후 팀 논의"))
    print(f"저장: {out}")
    if a.apply:
        apply_exclude(rows, Path(a.manifest))


def apply_exclude(rows, manifest):
    """거리 ≤ SAME(거의 같음)인 쌍에서 평가 쪽(val/test/bridge_holdout) 사진을 eval_exclude=True로 표시.
    split은 바꾸지 않는다. split_manifest.csv와 split별 CSV를 함께 고친다."""
    evals = {"val", "test", "bridge_holdout"}
    excl = {}
    for r in rows:
        if r["distance"] > SAME or r["split_a"] == r["split_b"]:
            continue
        for side in ("a", "b"):
            if r[f"split_{side}"] in evals:
                excl[r[f"image_{side}"]] = f"pHash {r['distance']} ↔ {r['image_b' if side == 'a' else 'image_a']}"
    man = manifest.parent
    for f in [manifest] + [man / f"{s}.csv" for s in ("train", "val", "test", "bridge_holdout")]:
        if not f.exists():
            continue
        m = pd.read_csv(f, encoding="utf-8-sig")
        if "eval_exclude_reason" not in m:
            m["eval_exclude_reason"] = ""
        m["eval_exclude_reason"] = m["eval_exclude_reason"].fillna("").astype(str)
        m.loc[m["eval_exclude"] & (m["eval_exclude_reason"] == ""), "eval_exclude_reason"] = "애매한 라벨"
        hit = m["image_name"].isin(excl)
        m.loc[hit, "eval_exclude"] = True
        m.loc[hit, "eval_exclude_reason"] = m.loc[hit, "image_name"].map(excl)
        m.to_csv(f, index=False, encoding="utf-8-sig")
    print(f"\n[--apply] eval_exclude=True 추가 {len(excl)}장 → manifests/*.csv (split은 그대로)")
    for n, why in sorted(excl.items()):
        print(f"  - {n}  ({why})")


if __name__ == "__main__":
    main()