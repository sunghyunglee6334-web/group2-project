"""
split_builder.py — 교과 8 Split v4 (묶음 단위 · 배정 직접 지정)

  v4에서 바뀐 점 (v1 → v4)
    - 묶음은 절대 쪼개지 않는다. T17_V 같은 '조각' 처리, Val 먼저(val_first), 조합 탐색을 모두 뺐다
    - 배정은 팀이 정한 표(POLICY["assignment"])대로 한다 → 누가 돌려도 같은 결과, 몇 초면 끝
    - 4-1 누수 검증에 예외가 없다 (같은 묶음·같은 time_group이 두 split에 걸치면 실패)
    - Class 6·이물만 장면처럼 '한 묶음에만 있는 것'은 평가할 수 없다고 보고서에 표시한다

  [1단계] 누수 방지 묶음 만들기
      1-1 촬영 시각 순 정렬
      1-2 인접 간격 Δt > gap_seconds 이면 새 묶음 → time_group (T00, T01 …)
      1-3 (선택) 같은 파일(MD5)·거의 같은 사진(pHash)이 있으면 묶음끼리 합침 → group_id
      1-4 같은 위치·다른 이물 사진 쌍 → merge(합침) 또는 flag(표시)
  [2단계] 묶음 속성: 장수 · 장면 · Class 구성 · 객체 수 · 빈 라벨 · 출처 · 애매한 라벨 · 날짜
  [3단계] 배정: POLICY["assignment"]에 적힌 묶음은 그 split, 나머지는 Train
  [4단계] 검증: 누수(예외 없음) · 장수 · 날짜 · 애매한 라벨 · 출처 비율 · Class/장면이 평가 쪽에 있는지
  [5단계] manifests 저장 (산출물 1) · 보고서
  [6단계] (선택) YOLO 폴더 복사 + dataset.yaml
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import os
import re
import shutil
from collections import Counter
from pathlib import Path

import pandas as pd

SPLITS = ["train", "val", "test", "bridge_holdout"]
SIZE_BINS = ["small", "medium", "large"]

# 교과 7 Class 번호·이름 (README 4장 · 번호 변경 금지) — dataset.yaml names
CLASS_NAMES = {0: "leaf_paper", 1: "plastic_stone_metal", 2: "branch", 3: "insect",
               4: "rubber_glove_unused", 5: "disease_browning", 6: "green_onion_pepper"}

DEFAULT_POLICY = {
    "name": "group_fixed_v4",
    "columns": {"image_id": "image_name", "image_path": "relative_path",
                "label_name": "label_name", "label_path": "label_relative_path",
                "source": "source_dataset", "scene": "scene_type",
                "bbox_count": "final_bbox_count", "issue": "issue", "note": "note"},
    # [1단계]
    "use_md5": True,
    "use_phash": False, "phash_max_distance": 5,         # pHash는 06_check_phash.py로 따로 확인 (팀 결정)
    "max_group_share": 0.20,                             # 한 묶음이 전체의 20% 넘으면 경고
    "scene_pair": {"enabled": True, "mode": "merge", "min_boxes": 2, "min_iou": 0.8, "min_pair_share": 0.2},
    # [2단계]
    "eval_classes": ["0", "1", "2", "3", "5", "6"],      # 평가할 Class (4 장갑은 데이터 없음)
    "size_bins": {"mode": "class_quantile", "q": [1 / 3, 2 / 3], "train_px": 640, "small": 32, "large": 96},
    "size_min_objects": 10,                              # [4-5] 객체가 이보다 적으면 크기 쏠림 판정 안 함
    "small_concentration": {"top_k": 5, "share": 0.5},   # [4-6] small 상위 5장이 split small의 50% 이상이면 경고
    "ambiguous_keywords": ["모호", "ambiguous", "불확실", "의심", "REVIEW"],
    "source_d1": "이물검출_학습데이터1",
    # [3단계] v5: v4-B에서 Bridge의 T09(병해 46%)를 T06과 맞바꿈 · Val·Test는 v4-B와 같음 · 나머지 Train
    "assignment": {
        "val": ["T01", "T03", "T07"],
        "test": ["T08", "T14"],
        "bridge_holdout": ["T06", "T11", "T16"],
    },
    "sizes": {"val": 66, "test": 75, "bridge_holdout": 151},   # train = 나머지 608. 다르면 실패
    # [4-1] '완화 3' 되돌림: 이 Class들은 Train 박스가 다른 split보다 많아야 함 (어기면 ❌)
    "train_most_classes": ["0", "1", "2", "3", "5", "6"],
    # [4단계] 역할별 확인 (어기면 '확인 필요'에 기록, 배정은 바꾸지 않음)
    "role_rules": {
        "val":            {"max_ambiguous": 1, "min_dates": 1, "source_band_pp": None},
        "test":           {"max_ambiguous": 1, "min_dates": 2, "source_band_pp": 10},
        "bridge_holdout": {"max_ambiguous": 1, "min_dates": 2, "source_band_pp": 10},
        "train":          {"source_band_pp": 10},
    },
    "class_min_objects": {"val": 5, "test": 5},          # Val·Test에 Class별 이 수보다 적으면 '평가 불가'로 표시
    "export": {"yolo_dir": "data/yolo", "bridge_dir": "data/bridge_holdout",
               "dataset_yaml": "configs/dataset.yaml",
               "manifest_dir": "manifests", "report_dir": "reports",
               "class_names": CLASS_NAMES},
}


class SplitError(RuntimeError):
    pass


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


# =====================================================================
# 준비 — manifest 읽기, 라벨·크기·애매한 라벨 계산
# =====================================================================
_TIME_RE = re.compile(r"(\d{6})_(\d{6})(\d{6})")


def _capture_time(name):
    m = _TIME_RE.search(str(name))
    if not m:
        raise SplitError(f"파일명에서 촬영 시각을 읽을 수 없음: {name}")
    d, t, us = m.groups()
    return pd.Timestamp(f"20{d[:2]}-{d[2:4]}-{d[4:]} {t[:2]}:{t[2:4]}:{t[4:]}.{us}")


def _file_index(root: Path | None) -> dict:
    """manifest 경로와 실제 폴더 구조가 달라도 '파일 이름'으로 찾기 위한 색인"""
    if root is None or not root.exists():
        return {}
    return {p.name: p for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".txt"}}


def _image_wh(p):
    """이미지 (너비, 높이). 읽을 수 없으면 None (정사각형으로 가정)"""
    if p is None:
        return None
    try:
        from PIL import Image
        with Image.open(p) as im:          # 헤더만 읽음 (빠름)
            return im.size
    except Exception:
        return None


def _box_area(w, h, wh, sb) -> float:
    """[2-4a] YOLO 비율 w·h → 긴 변을 train_px로 줄였을 때 넓이(px²)"""
    W, H = wh if wh else (1, 1)
    scale = sb["train_px"] / max(W, H)
    return (w * W * scale) * (h * H * scale)


def _area_bin(area, sb) -> str:
    """넓이 → small / medium / large (경계는 한 변 길이 px)"""
    return "small" if area < sb["small"] ** 2 else "large" if area >= sb["large"] ** 2 else "medium"


def load(manifest_path, data_root, policy, expected_total):
    col = policy["columns"]
    df = pd.read_csv(manifest_path, encoding="utf-8-sig")
    miss = [c for c in col.values() if c not in df.columns]
    if miss:
        raise SplitError(f"Manifest에 필요한 열이 없음: {miss}")
    if expected_total and len(df) != expected_total:
        raise SplitError(f"Manifest 행 수 {len(df)} ≠ 예상 {expected_total}")
    if df[col["image_id"]].duplicated().any():
        raise SplitError("image_name 중복")

    idx = _file_index(data_root)
    df["_img"] = [(data_root / r) if data_root and (data_root / r).exists() else idx.get(Path(n).name)
                  for r, n in zip(df[col["image_path"]], df[col["image_id"]])]
    df["_lbl"] = [(data_root / r) if data_root and (data_root / r).exists() else idx.get(Path(n).name)
                  for r, n in zip(df[col["label_path"]], df[col["label_name"]])]

    # 라벨 → 이미지별 클래스 목록
    df["_boxes"] = [[(str(int(float(t[0]))), *map(float, t[1:5]))
                     for t in (l.split() for l in p.read_text(encoding="utf-8").splitlines()) if len(t) == 5]
                    if p is not None else [] for p in df["_lbl"]]
    df["_classes"] = [[b[0] for b in bs] for bs in df["_boxes"]]

    # [2-4a] bbox 크기 구간 (학습 해상도 기준) — 4K 원본 기준이면 모두 '큰' 객체가 되므로 줄인 크기로 계산
    sb = dict(policy["size_bins"])
    whs = list(map(_image_wh, df["_img"]))
    areas = [[_box_area(b[3], b[4], wh, sb) for b in bs] for bs, wh in zip(df["_boxes"], whs)]
    if sb.get("mode") == "class_quantile":           # Class마다 따로 경계
        by_c = {}
        for bs, aa in zip(df["_boxes"], areas):
            for b, ar in zip(bs, aa):
                by_c.setdefault(b[0], []).append(ar)
        cut = {c: pd.Series(v).quantile(sb["q"]).tolist() for c, v in by_c.items()}
        df.attrs["size_bins"] = {"mode": "class_quantile",
                                 "small_px": {c: round(v[0] ** 0.5, 1) for c, v in sorted(cut.items())},
                                 "large_px": {c: round(v[1] ** 0.5, 1) for c, v in sorted(cut.items())}}
        df["_sizes"] = [[(b[0], "small" if ar < cut[b[0]][0] else "large" if ar >= cut[b[0]][1] else "medium")
                         for b, ar in zip(bs, aa)] for bs, aa in zip(df["_boxes"], areas)]
    elif sb.get("mode") == "quantile":                 # 우리 데이터 기준 경계 (넓이 → 한 변 길이로 기록)
        flat = pd.Series([a for aa in areas for a in aa])
        if len(flat):
            lo, hi = flat.quantile(sb["q"]).tolist()
            sb["small"], sb["large"] = lo ** 0.5, hi ** 0.5
    if sb.get("mode") != "class_quantile":
        df.attrs["size_bins"] = {"mode": sb.get("mode", "fixed"),
                                 "small_px": round(sb["small"], 1), "large_px": round(sb["large"], 1)}
        df["_sizes"] = [[(b[0], _area_bin(a, sb)) for b, a in zip(bs, aa)] for bs, aa in zip(df["_boxes"], areas)]
    df["n_small"] = [sum(1 for _, z in zs if z == "small") for zs in df["_sizes"]]
    df["has_label_file"] = df["_lbl"].notna()

    text = df[col["issue"]].fillna("").astype(str) + " " + df[col["note"]].fillna("").astype(str)
    df["label_ambiguous"] = text.str.contains("|".join(map(re.escape, policy["ambiguous_keywords"])),
                                              case=False, regex=True)
    df["is_background"] = df[col["bbox_count"]].fillna(0).astype(int) == 0
    df["_d1"] = df[col["source"]] == policy["source_d1"]
    df["capture_time"] = df[col["image_id"]].map(_capture_time)
    df["capture_date"] = df["capture_time"].dt.strftime("%m-%d")
    return df


# =====================================================================
# [1단계] 누수 방지 묶음 만들기
# =====================================================================
def step1_make_groups(df, gap_seconds, policy, issues, log):
    # [1-1] 촬영 시각 순 정렬
    df = df.sort_values("capture_time").reset_index(drop=True)

    # [1-2] 인접 간격 Δt > 기준값 → 새 묶음 (time_group)
    dt = df["capture_time"].diff().dt.total_seconds().fillna(0)
    df["delta_t"] = dt.round(1)
    df["time_group"] = (dt > gap_seconds).cumsum().map(lambda i: f"T{i:02d}")
    log.append(f"[1-2] Δt > {gap_seconds}s 기준 time_group {df['time_group'].nunique()}개")

    # [1-3] 같은 파일·거의 같은 사진이 있는 묶음끼리 합침 → group_id
    parent = {g: g for g in df["time_group"].unique()}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = sorted((find(a), find(b)))
        if ra != rb:
            parent[rb] = ra
            return True
        return False

    if df["_img"].notna().sum() == 0:
        issues.append("[1-3] 이미지 파일이 없어 해시 병합을 건너뜀")
        df["_md5"] = None
    else:
        df["_md5"] = [hashlib.md5(Path(p).read_bytes()).hexdigest() if p is not None else None for p in df["_img"]]
        if policy["use_md5"]:
            first = {}
            for tg, h in zip(df["time_group"], df["_md5"]):
                if h is None:
                    continue
                if h in first and union(first[h], tg):
                    issues.append(f"[1-3] 같은 파일(MD5) → {first[h]} + {tg} 병합")
                first.setdefault(h, tg)
        if policy["use_phash"]:
            try:
                import imagehash
                from PIL import Image
            except ImportError:
                issues.append("[1-3] imagehash가 없어 pHash 병합을 건너뜀 (pip install imagehash)")
            else:
                hs = [(tg, imagehash.phash(Image.open(p))) for tg, p in zip(df["time_group"], df["_img"]) if p is not None]
                for (ga, ha), (gb, hb) in itertools.combinations(hs, 2):
                    if find(ga) != find(gb) and ha - hb <= policy["phash_max_distance"] and union(ga, gb):
                        issues.append(f"[1-3] 거의 같은 사진(pHash) → {ga} + {gb} 병합")

    # [1-4] 같은 위치·다른 이물 (장면을 외우는지)
    pairs = _scene_pairs(df, find, policy) if policy["scene_pair"]["enabled"] else []
    if pairs:
        tg_pairs = sorted({tuple(sorted((df.at[a, "time_group"], df.at[b, "time_group"]))) for a, b, *_ in pairs})
        log.append(f"[1-4] 같은 위치·다른 이물 쌍 {len(pairs)}개 (묶음 쌍 {len(tg_pairs)}개)")
        if policy["scene_pair"]["mode"] == "merge":
            size = df["time_group"].value_counts()
            hit = {}
            for a, b, *_ in pairs:
                k = tuple(sorted((df.at[a, "time_group"], df.at[b, "time_group"])))
                hit.setdefault(k, (set(), set()))
                hit[k][0].add(a); hit[k][1].add(b)
            for (ga, gb), (sa, sb_) in hit.items():
                share = max(len(sa), len(sb_)) / min(size[ga], size[gb])
                if share >= policy["scene_pair"]["min_pair_share"] and union(ga, gb):
                    issues.append(f"[1-4] 같은 위치·다른 이물 → {ga} + {gb} 병합 (작은 묶음의 {share:.0%})")
        else:
            issues.append(f"[1-4] 같은 위치·다른 이물 쌍 {len(pairs)}개 표시만 함 (flag) → 4-7에서 split별 점검")
    df.attrs["scene_pairs"] = pairs

    members = {}
    for g in df["time_group"].unique():
        members.setdefault(find(g), []).append(g)
    gid = {g: "+".join(ms) for ms in members.values() for g in ms}
    df["group_id"] = df["time_group"].map(gid)
    df["same_bundle_split"] = False                    # v4: 묶음을 쪼개지 않음 (manifest 열 호환용)
    log.append(f"[1-3] group_id {df['group_id'].nunique()}개")

    size = df["group_id"].value_counts()
    log.append(f"[1-4] 묶음 크기: 최소 {size.min()} · 중앙값 {int(size.median())} · 최대 {size.max()}장")
    for g, n in size[size > len(df) * policy["max_group_share"]].items():
        issues.append(f"[1-4] 묶음 {g}가 큼: {n}장 ({n / len(df):.0%})")
    return df


def _box_iou(a, b):
    """YOLO (xc, yc, w, h) 두 박스의 IoU"""
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    iw, ih = max(0.0, min(ax2, bx2) - max(ax1, bx1)), max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def _layout_iou(ba, bb):
    """[1-5] 두 사진의 박스 위치가 얼마나 같은가 (Class 무시).
    IoU가 큰 박스끼리 하나씩 짝지어 평균 IoU (짝 못 찾은 박스는 0)"""
    cand = sorted(((_box_iou(x[1:], y[1:]), i, j) for i, x in enumerate(ba) for j, y in enumerate(bb)), reverse=True)
    used_a, used_b, total = set(), set(), 0.0
    for v, i, j in cand:
        if v <= 0:
            break
        if i not in used_a and j not in used_b:
            used_a.add(i); used_b.add(j); total += v
    return total / max(len(ba), len(bb))


def _scene_pairs(df, find, policy) -> list:
    """[1-5] 다른 묶음 + 박스 수 같음 + 박스 위치 IoU ≥ min_iou + Class 구성이 다름 → 쌍
    반환 [(행 a, 행 b, IoU, Class a, Class b), ...]"""
    thr = policy["scene_pair"]["min_iou"]
    rows = [(i, tg, bs) for i, tg, bs in zip(df.index, df["time_group"], df["_boxes"])
            if len(bs) >= policy["scene_pair"]["min_boxes"]]
    by_n = {}
    for r in rows:
        by_n.setdefault(len(r[2]), []).append(r)          # 박스 수가 같은 사진끼리만 비교 (속도)
    out = []
    for group in by_n.values():
        for (ia, ta, ba), (ib, tb, bb) in itertools.combinations(group, 2):
            if ta == tb or find(ta) == find(tb):
                continue                                    # 이미 같은 묶음
            ca, cb = sorted(b[0] for b in ba), sorted(b[0] for b in bb)
            if ca == cb:
                continue                                    # 이물이 같으면 1-3(pHash)이 맡음
            # 빠른 거르기: 박스 중심 평균이 멀면 건너뜀
            if abs(sum(b[1] for b in ba) - sum(b[1] for b in bb)) / len(ba) > 0.15 or \
               abs(sum(b[2] for b in ba) - sum(b[2] for b in bb)) / len(ba) > 0.15:
                continue
            v = _layout_iou(ba, bb)
            if v >= thr:
                out.append((ia, ib, round(v, 3), " ".join(ca), " ".join(cb)))
    return out


# =====================================================================
# [2단계] 묶음 속성
# =====================================================================
def diversity_bin(k: int) -> str:
    """[2-2] 클래스 합집합 크기 → 0 / 1-2 / 3-4 / 5-6"""
    return "0" if k == 0 else "1-2" if k <= 2 else "3-4" if k <= 4 else "5-6"


def step2_group_attributes(df, policy, has_labels) -> pd.DataFrame:
    col = policy["columns"]
    rows = []
    for g, d in df.groupby("group_id", sort=False):
        union = set().union(*d["_classes"])
        obj = Counter(c for cl in d["_classes"] for c in cl)
        row = {
            "group_id": g,
            "n_images": len(d),
            "scene_mode": d[col["scene"]].mode().iat[0],
            "class_union": " ".join(sorted(union, key=int)) if has_labels else "",
            "diversity": diversity_bin(len(union)) if has_labels else "unknown",
            "has_rare": "6" in union,                                        # Class 6 포함 (예전 스크립트 호환)
            "n_objects": int(sum(obj.values())),
            "bg_images": int(d["is_background"].sum()),
            "empty_ratio": round(d["is_background"].mean(), 3),
            "d1": int(d["_d1"].sum()),
            "ambiguous": int(d["label_ambiguous"].sum()),
            "dates": tuple(sorted(d["capture_date"].unique())),
            "first_time": d["capture_time"].min(),
        }
        for s_, n in d[col["scene"]].value_counts().items():
            row[f"scene_n:{s_}"] = int(n)
        for c in policy["eval_classes"]:
            row[f"obj_{c}"] = obj.get(c, 0)
        rows.append(row)
    gt = pd.DataFrame(rows).sort_values("first_time").set_index("group_id").fillna(0)
    gt["stratum"] = gt["scene_mode"] + "|" + gt["diversity"]
    return gt


# =====================================================================
# [3단계] 배정 — 팀이 정한 표대로 (나머지는 Train)
# =====================================================================
def step3_assign(gt, policy, log) -> dict:
    asg = policy["assignment"]
    named = [(g, r) for r, gs in asg.items() for g in gs]
    if any(r not in SPLITS or r == "train" for _, r in named):
        raise SplitError(f"[3단계] assignment 역할은 val / test / bridge_holdout만 적습니다: {list(asg)}")
    miss = [g for g, _ in named if g not in gt.index]
    if miss:
        raise SplitError(f"[3단계] 없는 묶음: {miss} (있는 묶음: {', '.join(gt.index)})")
    dup = [g for g, n in Counter(g for g, _ in named).items() if n > 1]
    if dup:
        raise SplitError(f"[3단계] 두 역할에 적힌 묶음: {dup}")
    role = {g: "train" for g in gt.index}
    role.update(dict(named))
    for r, want in policy["sizes"].items():
        n = int(gt.loc[[g for g, x in role.items() if x == r], "n_images"].sum())
        if n != want:
            raise SplitError(f"[3단계] {r} {n}장 ≠ sizes {want}장 (assignment 또는 sizes를 고치세요)")
        log.append(f"[3단계] {r} {n}장: {', '.join(g for g, x in role.items() if x == r)}")
    log.append(f"[3단계] train {int(gt.loc[[g for g, x in role.items() if x == 'train'], 'n_images'].sum())}장: 나머지 전부")
    return role


# =====================================================================
# [4단계] 검증
# =====================================================================
def step4_validate(df, gt, policy, has_labels):
    col = policy["columns"]
    # [4-1] 누수 — 예외 없음
    mixed = df.groupby("group_id")["split"].nunique()
    mixed_t = df.groupby("time_group")["split"].nunique()
    results = [
        ("모든 이미지가 하나의 split에만 속함", bool(df["split"].isin(SPLITS).all()), ""),
        ("같은 group_id가 여러 split에 걸치지 않음", bool((mixed == 1).all()), f"{mixed[mixed > 1].index.tolist()}"),
        ("같은 time_group이 여러 split에 걸치지 않음 (예외 없음)", bool((mixed_t == 1).all()),
         f"{mixed_t[mixed_t > 1].index.tolist()}"),
    ]
    if df["_md5"].notna().any():
        h = lambda rs: set(df.loc[df["split"].isin(rs), "_md5"].dropna())
        ov = h(["train", "val"]) & h(["test"])
        ob = h(["bridge_holdout"]) & h(["train", "val", "test"])
        results += [("Train·Val과 Test에 같은 이미지 없음", not ov, f"겹침 {len(ov)}"),
                    ("Bridge가 다른 split과 겹치지 않음", not ob, f"겹침 {len(ob)}")]

    # [4-2] split별 분포 비교표
    rows = []
    for s in SPLITS:
        d = df[df["split"] == s]
        row = {"split": s, "images": len(d), "groups": d["group_id"].nunique(),
               "d1_pct": round(d["_d1"].mean() * 100, 1) if len(d) else 0,
               "empty_pct": round(d["is_background"].mean() * 100, 1) if len(d) else 0,
               "ambiguous": int(d["label_ambiguous"].sum()),
               "dates": ",".join(sorted(d["capture_date"].unique()))}
        for k, v in d[col["scene"]].value_counts().items():
            row[f"scene:{k}"] = int(v)
        if has_labels:
            obj = Counter(c for cl in d["_classes"] for c in cl)
            for c in sorted(obj, key=int):
                row[f"class:{c}"] = obj[c]
        rows.append(row)
    dist = pd.DataFrame(rows).fillna(0)
    for c in dist.columns:
        if c.startswith(("scene:", "class:")):
            dist[c] = dist[c].astype(int)
    if has_labels:                                   # [4-1] Class별 Train 박스가 가장 많은가
        d_ = dist.set_index("split")
        for c in policy.get("train_most_classes", []):
            k = f"class:{c}"
            if k not in d_:
                continue
            others = {s: int(d_.at[s, k]) for s in SPLITS if s != "train"}
            top = max(others, key=others.get)
            results.append((f"Class {c}: Train 박스가 가장 많음", int(d_.at["train", k]) > others[top],
                            f"Train {int(d_.at['train', k])} ≤ {top} {others[top]}"))

    # [4-3] 역할별 확인 (배정은 바꾸지 않고 기록만)
    warn = []
    overall_d1 = df["_d1"].mean() * 100
    for s in SPLITS:
        rule, d = policy["role_rules"].get(s, {}), df[df["split"] == s]
        if not len(d):
            continue
        if rule.get("max_ambiguous") is not None and d["label_ambiguous"].sum() > rule["max_ambiguous"]:
            warn.append(f"[4-3] {s}: 애매한 라벨 {int(d['label_ambiguous'].sum())}장 (기준 ≤{rule['max_ambiguous']})")
        if rule.get("min_dates") and d["capture_date"].nunique() < rule["min_dates"]:
            warn.append(f"[4-3] {s}: 촬영 날짜 {d['capture_date'].nunique()}일 (기준 ≥{rule['min_dates']})")
        band = rule.get("source_band_pp")
        if band is not None and abs(d["_d1"].mean() * 100 - overall_d1) > band:
            warn.append(f"[4-3] {s}: 데이터1 비율 {d['_d1'].mean() * 100:.1f}% (전체 {overall_d1:.1f}±{band}%p 밖)")

    # [4-4] 평가할 수 있는가 — Class·장면이 Val·Test에 충분히 있는지, 한 묶음에만 있는지
    coverage = []
    if has_labels:
        d_ = dist.set_index("split")
        for c in policy["eval_classes"]:
            k = f"class:{c}"
            n = {s: int(d_.at[s, k]) if k in d_ else 0 for s in SPLITS}
            per_g = gt[f"obj_{c}"] if f"obj_{c}" in gt else pd.Series(dtype=int)
            top_g, top_share = (per_g.idxmax(), per_g.max() / per_g.sum()) if per_g.sum() else ("-", 0)
            need = policy["class_min_objects"]
            ok = all(n[s] >= need.get(s, 0) for s in ("val", "test"))
            coverage.append({"항목": f"Class {c}", **n, "평가": "가능" if ok else "불가",
                             "가장 많은 묶음": f"{top_g} {top_share:.0%}"})
            if not ok:
                why = f" — {top_g} 한 묶음에 {top_share:.0%}가 몰려 있음" if top_share >= 0.5 else ""
                warn.append(f"[4-4] Class {c}: Val {n['val']} · Test {n['test']}개 → 평가 불가{why}")
    for sc in sorted(df[col["scene"]].unique()):
        n = {s: int(((df["split"] == s) & (df[col["scene"]] == sc)).sum()) for s in SPLITS}
        g = df[df[col["scene"]] == sc]["group_id"].value_counts()
        coverage.append({"항목": f"장면 {sc}", **n, "평가": "가능" if n["val"] and n["test"] else "불가",
                         "가장 많은 묶음": f"{g.index[0]} {g.iat[0] / g.sum():.0%}"})
        if not (n["val"] and n["test"]) and n["train"]:
            warn.append(f"[4-4] 장면 {sc}: Val {n['val']} · Test {n['test']}장 → 이 장면 점수는 내지 않음")
    cov = pd.DataFrame(coverage)

    size_dist = pd.DataFrame()
    if has_labels:
        size_dist, w2 = _size_report(df, policy)                            # [4-5] [4-6]
        warn += w2
        warn += _scene_pair_report(df, policy)                              # [4-7]
    return results, dist, cov, warn, size_dist


def _size_report(df, policy):
    """[4-5] split × Class × 크기 표 + 전체와 차이 큰 칸 경고
       [4-6] 작은 객체가 몇 장에 몰렸는지 경고"""
    rows, warn = [], []
    long = [(s, c, z) for s, zs in zip(df["split"], df["_sizes"]) for c, z in zs if c in policy["eval_classes"]]
    t = pd.DataFrame(long, columns=["split", "class", "size"])
    if t.empty:
        return pd.DataFrame(), warn
    for (s, c), g in list(t.groupby(["split", "class"])) + [(("all", c), g) for c, g in t.groupby("class")]:
        n = len(g)
        row = {"split": s, "class": c, "objects": n}
        for z in SIZE_BINS:
            k = int((g["size"] == z).sum())
            row[z], row[f"{z}_pct"] = k, round(k / n * 100, 1)
        rows.append(row)
    sd = pd.DataFrame(rows).sort_values(["class", "split"]).reset_index(drop=True)
    allp = sd[sd["split"] == "all"].set_index("class")
    for _, r in sd[sd["split"].isin(["val", "test", "bridge_holdout"])].iterrows():
        if r["objects"] < policy["size_min_objects"]:
            continue
        diff = max(abs(r[f"{z}_pct"] - allp.at[r["class"], f"{z}_pct"]) for z in SIZE_BINS)
        if diff >= 30:
            warn.append(f"[4-5] {r['split']} Class {r['class']} 크기 분포가 전체와 {diff:.0f}%p 다름 "
                        f"(small {r['small_pct']}% / medium {r['medium_pct']}% / large {r['large_pct']}%)")
    sc = policy["small_concentration"]
    for s in SPLITS:
        ns = df.loc[df["split"] == s, "n_small"]
        if ns.sum() >= 10:
            top = ns.nlargest(sc["top_k"]).sum() / ns.sum()
            if top >= sc["share"]:
                warn.append(f"[4-6] {s}: 작은 객체 {int(ns.sum())}개 중 {top:.0%}가 사진 {sc['top_k']}장에 몰림")
    return sd, warn


def _scene_pair_report(df, policy) -> list:
    """[4-7] 같은 위치·다른 이물 쌍이 split을 넘나드는지 (flag 모드에서 의미 있음)"""
    pairs = df.attrs.get("scene_pairs", [])
    if not pairs:
        return []
    sp = df["split"]
    cross = Counter(tuple(sorted((sp[a], sp[b]))) for a, b, *_ in pairs if sp[a] != sp[b])
    if not cross:
        return []
    return ["[4-7] 같은 위치·다른 이물 쌍이 split을 넘나듦: "
            + ", ".join(f"{a}↔{b} {n}쌍" for (a, b), n in cross.most_common())
            + " → 평가 때 이 사진만 따로 점수를 내 '장면 외우기' 점검"]


# =====================================================================
# [5단계] 저장 — manifests (산출물 1) · 보고서
# =====================================================================
KEY_COLS = ["image_name", "split", "group_id", "time_group", "capture_time", "delta_t",
            "eval_exclude", "same_bundle_split", "label_ambiguous", "is_background",
            "yolo_image_path", "yolo_label_path", "dataset_version", "policy_version"]


def _yolo_paths(df, project_root: Path, policy):
    """[5-1] 각 이미지가 복사될 YOLO 경로를 미리 정해 manifest에 적는다 (복사 여부와 무관)"""
    ex = policy["export"]
    col = policy["columns"]
    img, lbl = [], []
    for name, split in zip(df[col["image_id"]], df["split"]):
        stem = Path(name).stem
        if split == "bridge_holdout":
            base = Path(ex["bridge_dir"])
            img.append((base / "images" / name).as_posix())
            lbl.append((base / "labels" / f"{stem}.txt").as_posix())
        else:
            base = Path(ex["yolo_dir"])
            img.append((base / "images" / split / name).as_posix())
            lbl.append((base / "labels" / split / f"{stem}.txt").as_posix())
    df["yolo_image_path"], df["yolo_label_path"] = img, lbl


def step5_save_manifests(df, project_root: Path, policy) -> list:
    """[5-2] manifest_dir에 5개 파일 저장 → [5-3] 다시 읽어서 확인"""
    man_dir = policy["export"]["manifest_dir"]
    man = project_root / man_dir
    man.mkdir(parents=True, exist_ok=True)
    out = df.drop(columns=[c for c in df.columns if c.startswith("_")])
    out = out[[c for c in KEY_COLS if c in out] + [c for c in out if c not in KEY_COLS]]
    out.to_csv(man / "split_manifest.csv", index=False, encoding="utf-8-sig")
    for s in SPLITS:
        out[out["split"] == s].to_csv(man / f"{s}.csv", index=False, encoding="utf-8-sig")

    # [5-3] 저장된 파일 확인: 장수, 합계, 서로 겹치지 않는지
    res = []
    full = pd.read_csv(man / "split_manifest.csv", encoding="utf-8-sig")
    names = {}
    for s in SPLITS:
        part = pd.read_csv(man / f"{s}.csv", encoding="utf-8-sig")
        names[s] = set(part["image_name"])
        want = int((df["split"] == s).sum())
        res.append((f"{man_dir}/{s}.csv 저장 ({want}장)", len(part) == want, f"{len(part)}장"))
    union = set().union(*names.values())
    overlap = sum(len(names[a] & names[b]) for a, b in itertools.combinations(SPLITS, 2))
    res.append(("split_manifest.csv = 네 파일의 합 (겹침 없음)",
                len(full) == len(union) == len(df) and overlap == 0,
                f"전체 {len(full)} / 합집합 {len(union)} / 겹침 {overlap}"))
    return res


# =====================================================================
# [6단계] (선택) YOLO 폴더 복사
# =====================================================================
def _clean_files(folder: Path, project_root: Path):
    data_dir = (project_root / "data").resolve()
    if data_dir not in folder.resolve().parents:
        raise SplitError(f"정리 대상이 data/ 밖: {folder}")
    if folder.exists():
        for p in folder.iterdir():
            if p.is_file():
                p.unlink()


def step6_copy_yolo(df, data_root, project_root: Path, policy, issues) -> list:
    ex = policy["export"]
    missing = int(df["_img"].isna().sum())
    if missing:                                     # 이미지가 없으면 복사만 건너뜀 (manifests는 이미 저장됨)
        issues.append(f"[6단계] 이미지 {missing}장을 찾지 못해 YOLO 복사를 건너뜀 (manifests는 저장됨)")
        return []
    yolo, bridge = project_root / ex["yolo_dir"], project_root / ex["bridge_dir"]
    if data_root is not None:
        src = data_root.resolve()
        for dst in (yolo.resolve(), bridge.resolve()):
            if dst == src or src in dst.parents or dst in src.parents:
                raise SplitError(f"복사 대상 {dst}가 원본 {src}와 겹침")
    dirs = {s: (yolo / "images" / s, yolo / "labels" / s) for s in ("train", "val", "test")}
    dirs["bridge_holdout"] = (bridge / "images", bridge / "labels")
    for pair in dirs.values():                       # [6-1] 이전 Split 잔여 파일 제거 (누수 방지)
        for d in pair:
            _clean_files(d, project_root)
            d.mkdir(parents=True, exist_ok=True)
    for _, r in df.iterrows():                       # [6-2] manifest에 적힌 경로로 복사
        shutil.copy2(r["_img"], project_root / r["yolo_image_path"])
        dst = project_root / r["yolo_label_path"]
        if r["_lbl"] is not None and not pd.isna(r["_lbl"]):
            shutil.copy2(r["_lbl"], dst)
        else:
            dst.write_text("", encoding="utf-8")
    res = []                                         # [6-3] 폴더별 장수 확인
    for s, (img_dir, lbl_dir) in dirs.items():
        want = int((df["split"] == s).sum())
        ni = sum(p.is_file() for p in img_dir.iterdir())
        nl = sum(p.is_file() for p in lbl_dir.iterdir())
        res.append((f"{s} 폴더 복사 ({want}장)", ni == want and nl == want, f"이미지 {ni} / 라벨 {nl}"))
    write_dataset_yaml(project_root, policy)          # [6-4] dataset.yaml (Bridge 제외)
    return res


def write_dataset_yaml(project_root: Path, policy) -> Path:
    """[6-4] dataset.yaml — path 줄 없이 yaml 위치 기준 상대경로 (누구 PC에서든 같은 파일로 학습)"""
    ex = policy["export"]
    y = Path(project_root) / ex["dataset_yaml"]
    y.parent.mkdir(parents=True, exist_ok=True)
    rel = Path(os.path.relpath(Path(project_root) / ex["yolo_dir"], y.parent)).as_posix()
    names = "\n".join(f"  {k}: {v}" for k, v in sorted(ex["class_names"].items()))
    y.write_text(f"# {policy['name']} · 03_build_split.py가 생성\n"
                 "# Bridge Holdout(data/bridge_holdout)은 교과 8 개발에 사용하지 않으므로 넣지 않음\n"
                 f"train: {rel}/images/train\nval: {rel}/images/val\ntest: {rel}/images/test\n"
                 f"names:\n{names}\n", encoding="utf-8")
    return y


def _md(t) -> str:
    """표 → Markdown. tabulate가 없으면 고정폭 글자 표로 대신 (실행이 멈추지 않게)"""
    try:
        return t.to_markdown(index=False)
    except ImportError:
        return "```\n" + t.to_string(index=False) + "\n```"


def write_reports(df, gt, dist, cov, results, issues, log, meta, project_root: Path, policy):
    ex = policy["export"]
    rep = project_root / ex["report_dir"]
    rep.mkdir(parents=True, exist_ok=True)
    dist.to_csv(rep / "dataset_summary.csv", index=False, encoding="utf-8-sig")
    cov.to_csv(rep / "coverage.csv", index=False, encoding="utf-8-sig")
    size_dist = df.attrs.get("size_distribution", pd.DataFrame())
    if not size_dist.empty:
        size_dist.to_csv(rep / "size_distribution.csv", index=False, encoding="utf-8-sig")
    sha = hashlib.sha256((project_root / ex["manifest_dir"] / "split_manifest.csv").read_bytes()).hexdigest()
    g = gt.reset_index()[["group_id", "n_images", "scene_mode", "class_union", "n_objects",
                          "empty_ratio", "d1", "ambiguous", "split"]]
    g.insert(2, "dates", gt["dates"].map(",".join).values)
    mark = lambda ok: "✅" if ok else "❌"
    (rep / "split_report.md").write_text("\n".join([
        f"# Split 기록 — {meta['dataset_version']}", "",
        f"- 정책: {policy['name']} · gap {meta['gap']}s · 배정 직접 지정 (묶음 쪼개기 없음)",
        f"- 산출물 1: {ex['manifest_dir']}/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv",
        f"- split_manifest.csv SHA256: `{sha}`", "",
        "## 묶음과 배정", "", g.pipe(_md), "",
        "## split별 분포", "", dist.pipe(_md), "",
        "## 평가할 수 있는가 (Val·Test에 있는지)", "", cov.pipe(_md), "",
        "## Class × bbox 크기", "", (size_dist.pipe(_md) if not size_dist.empty else "- 라벨 없음"), "",
        "## 검증", "", *[f"- {mark(ok)} {n}" + ("" if ok else f" — {d}") for n, ok, d in results], "",
        "## 확인 필요", "", *([f"- {x}" for x in issues] or ["- 없음"]), "",
        "## 실행 로그", "", *[f"- {x}" for x in log]]) + "\n", encoding="utf-8")


# =====================================================================
# 진입점
# =====================================================================
def build_split(manifest_path, data_root=None, project_root=".", dataset_version="TODO",
                gap_seconds=300, seed=42, expected_total=900, save=False, copy_images=None,
                policy=None, **_):
    """반환 (df, issues). df.attrs에 groups / distribution / coverage / results / log 저장
    save        : True면 manifests + 보고서 저장 ([5단계])
    copy_images : True면 YOLO 폴더로 복사 ([6단계]). None이면 save와 같은 값"""
    policy = _merge(DEFAULT_POLICY, policy)
    project_root = Path(project_root)
    data_root = Path(data_root) if data_root and Path(data_root).exists() else None
    copy_images = save if copy_images is None else copy_images
    issues, log = [], []

    df = load(Path(manifest_path), data_root, policy, expected_total)
    has_labels = bool(df["has_label_file"].any())
    if not has_labels:
        issues.append("라벨 파일이 없어 Class 구성을 계산하지 못함")
    df = step1_make_groups(df, gap_seconds, policy, issues, log)                   # [1단계]
    gt = step2_group_attributes(df, policy, has_labels)                            # [2단계]
    role = step3_assign(gt, policy, log)                                           # [3단계]
    df["split"] = df["group_id"].map(role)
    gt["split"] = gt.index.map(role)
    df["eval_exclude"] = df["label_ambiguous"] & df["split"].isin(["test", "bridge_holdout"])
    if df["eval_exclude"].any():
        issues.append("Test·Bridge의 애매한 라벨 → eval_exclude=True: "
                      + ", ".join(df.loc[df["eval_exclude"], policy["columns"]["image_id"]]))
    results, dist, cov, warn, size_dist = step4_validate(df, gt, policy, has_labels)   # [4단계]
    df.attrs["size_distribution"] = size_dist
    issues += warn
    df["dataset_version"], df["policy_version"] = dataset_version, policy["name"]
    _yolo_paths(df, project_root, policy)

    if save:
        results += step5_save_manifests(df, project_root, policy)                  # [5단계]
        log.append(f"[5단계] {policy['export']['manifest_dir']}/ 저장")
    if copy_images:
        results += step6_copy_yolo(df, data_root, project_root, policy, issues)    # [6단계]
    if save:
        write_reports(df, gt, dist, cov, results, issues, log,
                      {"dataset_version": dataset_version, "gap": gap_seconds}, project_root, policy)
    issues += [f"검증 실패: {n} — {d}" for n, ok, d in results if not ok]
    df.attrs.update(groups=gt, distribution=dist, coverage=cov, results=results, log=log,
                    scene_pairs=df.attrs.get("scene_pairs", []))
    return df, issues
