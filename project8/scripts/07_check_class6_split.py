"""
07_check_class6_split.py — 파·고추(Class 6) 묶음(T00)을 시간순으로 나눠 '참고값'을 낼 수 있는지 확인 (Split은 바꾸지 않음)

실행 (project8 폴더에서, 03_build_split_v5.py 다음에):
    python scripts/07_check_class6_split.py
    python scripts/07_check_class6_split.py --group T00 --ref 10 --gap 5    직접 지정

입력 : manifests/split_manifest.csv, data/final/images, data/final/labels
출력 : reports/class6_split_check.csv (자르는 방법별 결과), 화면 요약

확인하는 것
  [1] 묶음 안 사진별 Class 6 박스 수 (시간순) — 들쭉날쭉하면 중간에 파·고추를 새로 덜어 왔을 가능성
  [2] 앞부분 Train · 경계 버림 · 뒷부분 참고용으로 자를 때
      - 양쪽 Class 6 박스 수
      - 참고용 사진 ↔ Train 쪽 사진의 가장 가까운 pHash 거리 (5 이하 = 거의 같은 사진)
  pHash는 '같은 사진'만 잡고 '같은 파 조각'은 못 잡음 → 통과해도 참고값은 낙관적인 값
"""
from pathlib import Path
import argparse
import importlib.util
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAME, SIMILAR = 5, 10
CLASS = "6"
MIN_REF_BOXES = 10                 # 참고용 쪽에 이보다 적으면 점수가 너무 흔들림

# 06_check_phash_v5.py의 pHash 계산을 그대로 씀
_spec = importlib.util.spec_from_file_location("phash", Path(__file__).with_name("06_check_phash_v5.py"))
_ph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ph)


def class_counts(lbl: Path | None) -> dict:
    out = {}
    if lbl is None or not lbl.exists():
        return out
    for line in lbl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = line.split()[0]
            out[c] = out.get(c, 0) + 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=PROJECT_ROOT / "manifests" / "split_manifest.csv")
    ap.add_argument("--data", default=PROJECT_ROOT / "data" / "final")
    ap.add_argument("--group", default=None, help="기본: Class 6 박스가 가장 많은 묶음")
    ap.add_argument("--ref", type=int, nargs="*", default=[8, 10, 12, 15], help="뒷부분 참고용 장수")
    ap.add_argument("--gap", type=int, nargs="*", default=[3, 5], help="경계에서 버릴 장수")
    ap.add_argument("--out", default=PROJECT_ROOT / "reports" / "class6_split_check.csv")
    a = ap.parse_args()

    df = pd.read_csv(a.manifest, encoding="utf-8-sig")
    data = Path(a.data)
    imgs = {p.name: p for p in data.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}}
    lbls = {p.stem: p for p in data.rglob("*.txt")}
    df["_img"] = df["image_name"].map(imgs)
    df["_c"] = [class_counts(lbls.get(Path(n).stem)) for n in df["image_name"]]
    df["c6"] = [c.get(CLASS, 0) for c in df["_c"]]

    total6 = int(df["c6"].sum())
    by_g = df.groupby("time_group")["c6"].sum().sort_values(ascending=False)
    g = a.group or by_g.index[0]
    print(f"Class 6 전체 {total6}개 · 묶음별 상위: " + ", ".join(f"{k} {v}" for k, v in by_g.head(4).items()))

    t = df[df["time_group"] == g].sort_values("capture_time").reset_index(drop=True)
    if t["_img"].isna().any():
        sys.exit(f"이미지를 찾지 못함: {t['_img'].isna().sum()}장 (--data 경로 확인)")
    print(f"\n[1] {g}: {len(t)}장 · {t['capture_time'].iloc[0]} ~ {t['capture_time'].iloc[-1]} · "
          f"Class 6 {int(t['c6'].sum())}개 ({t['c6'].sum() / max(total6, 1):.0%}) · 지금 split {t['split'].iloc[0]}")
    print("  사진별 Class 6 박스 (시간순):", " ".join(map(str, t["c6"])))
    nz = t.loc[t["c6"] > 0, "c6"]
    if len(nz):
        print(f"  박스 수 범위 {nz.min()}~{nz.max()} · 평균 {nz.mean():.1f} · 0개인 사진 {int((t['c6'] == 0).sum())}장")
        print("  → 범위가 좁으면 같은 파·고추를 계속 옮겨 찍은 것 (누수 위험 큼)" if nz.max() - nz.min() <= 2
              else "  → 들쭉날쭉함: 중간에 새로 덜어 왔을 수 있음 (그래도 같은 재료일 수 있음)")
    other = {}
    for c in t["_c"]:
        for k, v in c.items():
            if k != CLASS:
                other[k] = other.get(k, 0) + v
    if other:
        print("  같은 묶음의 다른 Class:", ", ".join(f"Class {k} {v}" for k, v in sorted(other.items())))

    print(f"\npHash 계산 중 ({len(t)}장)…", flush=True)
    t["_h"] = _ph.phash_all(t["_img"])
    near = [t["_h"][i] - t["_h"][i + 1] for i in range(len(t) - 1)]
    print(f"  바로 옆 사진 거리: 최소 {min(near)} · 중앙값 {int(pd.Series(near).median())} · 최대 {max(near)}")

    print(f"\n[2] 자르는 방법별 (앞 Train · 경계 버림 · 뒤 참고용)")
    rows = []
    for ref in a.ref:
        for gap in a.gap:
            n_tr = len(t) - ref - gap
            if n_tr <= 0:
                continue
            tr, rf = t.iloc[:n_tr], t.iloc[n_tr + gap:]
            dmin = [min(r - x for x in tr["_h"]) for r in rf["_h"]]
            row = {"group": g, "ref": ref, "gap": gap, "train_images": n_tr,
                   "train_c6": int(tr["c6"].sum()), "ref_c6": int(rf["c6"].sum()),
                   "min_dist": min(dmin), "ref_same(≤5)": sum(d <= SAME for d in dmin),
                   "ref_similar(≤10)": sum(d <= SIMILAR for d in dmin),
                   "cut_after": tr["image_name"].iloc[-1], "ref_from": rf["image_name"].iloc[0]}
            ok = row["ref_c6"] >= MIN_REF_BOXES and row["ref_same(≤5)"] == 0
            row["판정"] = "참고값 가능" if ok else ("박스 부족" if row["ref_c6"] < MIN_REF_BOXES else "거의 같은 사진 있음")
            rows.append(row)
    res = pd.DataFrame(rows)
    print(res.drop(columns=["group", "cut_after", "ref_from"]).to_string(index=False))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(out, index=False, encoding="utf-8-sig")

    good = res[res["판정"] == "참고값 가능"]
    print()
    if good.empty:
        print("결론: 이 묶음은 나눠도 참고값을 내기 어려움 → 'Class 6 평가 불가'로 두는 게 맞음")
    else:
        b = good.sort_values(["ref_similar(≤10)", "gap", "ref"], ascending=[True, False, True]).iloc[0]   # Train을 가장 적게 빼는 방법
        print(f"결론: 참고값만 가능 — 예) 뒤 {b['ref']}장 참고용 · 경계 {b['gap']}장 버림 · "
              f"Train Class 6 {b['train_c6']}개 / 참고용 {b['ref_c6']}개")
        print("  · 참고용 사진은 Val·Test에 섞지 말고 따로 평가 (Val 점수·평균에 넣지 않음)")
        print("  · 보고서에 '같은 촬영 묶음 안에서 나눈 낙관적 참고값'이라고 적기")
        print(f"  · 쓰려면 참고용 + 경계 {b['ref'] + b['gap']}장을 Train에서 빼고 다시 학습해야 함")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
