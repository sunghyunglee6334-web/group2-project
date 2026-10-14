"""
split_builder.py — 교과 8 Split MVP (그룹 단위 층화 배정)

  [1단계] 누수 방지 그룹 만들기 (아래에서 위로 합침)
      1-1 촬영 시각 순 정렬
      1-2 인접 간격 Δt > 기준값이면 새 그룹 → time_group
      1-3 (선택) 해시 유사도가 높은 이미지가 있는 그룹끼리 병합 → group_id
      1-4 그룹 크기 분포 확인
  [2단계] 그룹 속성 계산 (이미지 한 장이 아니라 그룹 기준)
      2-1 scene_type 최빈값      2-2 클래스 합집합 → 다양성 구간 0 / 1-2 / 3-4 / 5-6
      2-3 희소 클래스 포함 여부   2-4 객체 수, 빈 라벨 비율 (+ 출처 비율, 애매한 라벨 수)
  [3단계] group_id 단위 층화 배정 (bridge_holdout → test → val → train)
      3-1 층(stratum) = scene_type 최빈값 × 클래스 다양성 구간
      3-2 Train 보호 그룹 (층에 그룹이 하나뿐 / 희소 클래스가 몰린 그룹)
      3-3 조합 탐색: 장수를 정확히 맞추고, Bridge·Test·Val 점수 합이 가장 작은 배정 선택
          점수 = 층 + 장면(이미지 수) + Class 객체 비율 + 배경 비율 차이
          필수 = Train의 Class별 객체 수가 가장 많음 · 배경 절반 이상 Train · Val/Test Class 최소 개수
      → 같은 group_id는 반드시 같은 split
  [4단계] 검증
      4-1 그룹이 여러 split에 걸치지 않는지   4-2 split별 분포 비교표
  [5단계] manifests/ 저장 (산출물 1)  ← save=True
      split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv + 저장 후 다시 읽어 확인
  [6단계] (선택) YOLO 폴더 복사       ← copy_images=True
      data/yolo/{images,labels}/{train,val,test}, data/bridge_holdout/{images,labels}, configs/dataset.yaml
  (기록) reports/dataset_summary.csv, reports/split_report.md
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import re
import shutil
from collections import Counter
from pathlib import Path

import pandas as pd

SPLITS = ["train", "val", "test", "bridge_holdout"]
ASSIGN_ORDER = ["bridge_holdout", "test", "val"]       # train = 나머지

DEFAULT_POLICY = {
    "name": "group_stratified_mvp",
    "columns": {"image_id": "image_name", "image_path": "relative_path",
                "label_name": "label_name", "label_path": "label_relative_path",
                "source": "source_dataset", "scene": "scene_type",
                "bbox_count": "final_bbox_count", "issue": "issue", "note": "note"},
    # [1단계]
    "use_md5": True,
    "use_phash": True, "phash_max_distance": 5,          # TODO(기준선)
    "max_group_share": 0.20,                             # [1-4] 한 그룹이 전체의 20% 넘으면 경고
    # [2단계]
    "rare_classes": ["6"],                               # [2-3] 희소 클래스
    "eval_classes": ["0", "1", "2", "3", "5"],
    "ambiguous_keywords": ["모호", "ambiguous", "불확실", "의심", "REVIEW"],
    "source_d1": "이물검출_학습데이터1",
    # [3단계]
    "sizes": {"bridge_holdout": 150, "test": 75, "val": 75},   # train = 나머지 (600)
    "size_tolerance": 0,                                 # 0 = 장수 정확히
    "rare_protect_share": 0.4,                           # [3-2] 희소 클래스 이미지의 40% 이상 가진 그룹 → Train
    "pinned_train": [],                                  # [3-2] 직접 고정할 group_id (예: ["G17"])
    "role_rules": {                                      # [3-3] 역할별 필수 조건
        "bridge_holdout": {"max_ambiguous": 1, "min_dates": 2, "source_band_pp": 10},
        "test":           {"max_ambiguous": 1, "min_dates": 2, "source_band_pp": 10},
        "val":            {"max_ambiguous": 1, "min_dates": 1, "source_band_pp": None},
        "train":          {"source_band_pp": 10},
    },
    "max_groups_per_role": 6,
    "max_candidates_per_role": 300,                      # 역할마다 점수 좋은 후보 몇 개까지 볼지 (속도)
    # [3-3] 점수 = 전체 구성과의 차이 (작을수록 좋음)
    "score_weights": {"stratum": 0.5, "scene": 1.0, "class": 1.0, "background": 1.0},
    # [3-3] 꼭 지킬 조건 (Class·배경)
    "class_min_objects": {"val": 5, "test": 5},          # TODO(기준선): Val·Test에 Class별 최소 객체 수
    "train_min_background_share": 0.5,                   # 배경(빈 라벨) 이미지의 50% 이상은 Train
    "train_majority": True,                              # Class마다 Train 객체 수 ≥ 다른 split
    # 위 조건을 모두 만족하는 배정이 없으면, 아래 순서로 하나씩 풀어서 다시 찾는다 (풀린 조건은 issues에 기록)
    # 장수·날짜·애매한 라벨·출처 비율은 풀지 않는다
    "relax_steps": [
        ("class_min_objects", {}, "Val·Test Class별 최소 객체 수"),
        ("train_min_background_share", 0.3, "배경 이미지 Train 비율 50% → 30%"),
        ("train_majority", False, "Train Class 객체 수가 가장 많아야 함"),
        ("train_min_background_share", 0.0, "배경 이미지 Train 비율 조건"),
    ],
    # (저장)
    "export": {"yolo_dir": "data/yolo", "bridge_dir": "data/bridge_holdout",
               "dataset_yaml": "configs/dataset.yaml",
               "class_names": {i: f"class_{i}" for i in range(7)}},   # TODO(기준선): 클래스 이름
}


class SplitError(RuntimeError):
    pass


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


# =====================================================================
# 준비: Manifest·이미지·라벨 읽기
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
    df["_classes"] = [[str(int(float(l.split()[0]))) for l in p.read_text(encoding="utf-8").splitlines()
                       if len(l.split()) == 5] if p is not None else []
                      for p in df["_lbl"]]
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
# [1단계] 누수 방지 그룹 만들기
# =====================================================================
def step1_make_groups(df, gap_seconds, policy, issues, log):
    # [1-1] 촬영 시각 순 정렬
    df = df.sort_values("capture_time").reset_index(drop=True)

    # [1-2] 인접 간격 Δt > 기준값 → 새 그룹 (time_group)
    dt = df["capture_time"].diff().dt.total_seconds().fillna(0)
    df["delta_t"] = dt.round(1)
    df["time_group"] = (dt > gap_seconds).cumsum().map(lambda i: f"T{i:02d}")
    log.append(f"[1-2] Δt > {gap_seconds}s 기준 time_group {df['time_group'].nunique()}개")

    # [1-3] (선택) 해시 유사도가 높은 이미지가 있으면 그 time_group끼리 병합 → group_id
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

    have_img = df["_img"].notna().sum()
    if have_img == 0:
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
    members = {}
    for g in df["time_group"].unique():
        members.setdefault(find(g), []).append(g)
    gid = {g: "+".join(ms) for ms in members.values() for g in ms}
    df["group_id"] = df["time_group"].map(gid)
    log.append(f"[1-3] group_id {df['group_id'].nunique()}개")

    # [1-4] 그룹 크기 분포 확인
    size = df["group_id"].value_counts()
    log.append(f"[1-4] 그룹 크기: 최소 {size.min()} · 중앙값 {int(size.median())} · 최대 {size.max()}장")
    for g, n in size[size > len(df) * policy["max_group_share"]].items():
        issues.append(f"[1-4] 그룹 {g}가 너무 큼: {n}장 ({n / len(df):.0%})")
    return df


# =====================================================================
# [2단계] 그룹 속성 계산
# =====================================================================
def diversity_bin(k: int) -> str:
    """[2-2] 클래스 합집합 크기 → 0 / 1-2 / 3-4 / 5-6"""
    return "0" if k == 0 else "1-2" if k <= 2 else "3-4" if k <= 4 else "5-6"


def step2_group_attributes(df, policy, has_labels) -> pd.DataFrame:
    col = policy["columns"]
    scenes = sorted(df[col["scene"]].unique())
    rows = []
    for g, d in df.groupby("group_id", sort=False):
        union = set().union(*d["_classes"])                                  # [2-2] 클래스 합집합
        obj = Counter(c for cl in d["_classes"] for c in cl)
        img = Counter(c for cl in d["_classes"] for c in set(cl))
        sc = d[col["scene"]].value_counts()
        row = {
            "group_id": g,
            "n_images": len(d),
            "scene_mode": d[col["scene"]].mode().iat[0],                     # [2-1] scene_type 최빈값
            "class_union": " ".join(sorted(union, key=int)) if has_labels else "",
            "diversity": diversity_bin(len(union)) if has_labels else "unknown",
            "has_rare": bool(union & set(policy["rare_classes"])),           # [2-3] 희소 클래스 포함
            "n_objects": int(sum(obj.values())),                             # [2-4] 객체 수
            "bg_images": int(d["is_background"].sum()),                      # [2-4] 빈 라벨(배경) 이미지 수
            "empty_ratio": round(d["is_background"].mean(), 3),              # [2-4] 빈 라벨 비율
            "d1": int(d["_d1"].sum()),
            "ambiguous": int(d["label_ambiguous"].sum()),
            "dates": tuple(sorted(d["capture_date"].unique())),
            "first_time": d["capture_time"].min(),
        }
        for s_ in scenes:                                                    # [2-1] 장면별 이미지 수 (최빈값만 보면
            row[f"scene_n:{s_}"] = int(sc.get(s_, 0))                        #  T03처럼 섞인 그룹의 배경을 놓침)
        for c in sorted(set(obj) | set(policy["eval_classes"]) | set(policy["rare_classes"]), key=int):
            row[f"obj_{c}"], row[f"img_{c}"] = obj.get(c, 0), img.get(c, 0)
        rows.append(row)
    gt = pd.DataFrame(rows).sort_values("first_time").set_index("group_id")
    gt["stratum"] = gt["scene_mode"] + "|" + gt["diversity"]                 # [3-1] 층 키
    return gt


# =====================================================================
# [3단계] group_id 단위 층화 배정
# =====================================================================
def _protected(gt, policy, log) -> set:
    """[3-2] Train 보호 그룹"""
    prot = {}
    for g in policy["pinned_train"]:
        if g in gt.index:
            prot[g] = "직접 고정"
    counts = gt["stratum"].value_counts()
    for g, s in gt["stratum"].items():
        if counts[s] == 1 and g not in prot:
            prot[g] = f"층 '{s}'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)"
    for c in policy["rare_classes"]:
        tot = gt.get(f"img_{c}", pd.Series(dtype=int)).sum()
        for g in gt.index:
            if tot and g not in prot and gt.at[g, f"img_{c}"] / tot >= policy["rare_protect_share"]:
                prot[g] = f"희소 Class {c} 이미지의 {gt.at[g, f'img_{c}'] / tot:.0%} 보유"
    for g, why in prot.items():
        log.append(f"[3-2] Train 보호: {g} — {why}")
    return set(prot)


def _profile(sub, cols) -> pd.Series:
    """[3-3] 조합의 구성 비율 (합 1). cols 열의 합을 비율로 바꾼다"""
    v = sub[cols].sum()
    return v / v.sum() if v.sum() else v * 0


def _score(sub, ref, policy) -> dict:
    """[3-3] 전체와 얼마나 다른가 (0 = 전체와 같음). 항목별 L1 거리 × 가중치"""
    w = policy["score_weights"]
    parts = {
        "stratum": float((sub.groupby("stratum")["n_images"].sum() / sub["n_images"].sum())
                         .reindex(ref["stratum"].index, fill_value=0).sub(ref["stratum"]).abs().sum()),
        "scene": float(_profile(sub, ref["scene_cols"]).sub(ref["scene"]).abs().sum()),
        "class": float(_profile(sub, ref["class_cols"]).sub(ref["class"]).abs().sum()) if ref["class_cols"] else 0.0,
        "background": abs(sub["bg_images"].sum() / sub["n_images"].sum() - ref["bg"]) * 10,
    }
    parts["total"] = sum(parts[k] * w[k] for k in w)
    return parts


def _check(role, sub, overall_d1, policy, all_strata=None) -> list:
    rule, out = policy["role_rules"][role], []
    n = int(sub["n_images"].sum())
    if role != "train":
        want, tol = policy["sizes"][role], policy["size_tolerance"]
        if abs(n - want) > tol:
            out.append(f"{role}:장수({want}±{tol})")
        if sub["ambiguous"].sum() > rule["max_ambiguous"]:
            out.append(f"{role}:애매한 라벨(≤{rule['max_ambiguous']})")
        if len(set().union(*sub["dates"])) < rule["min_dates"]:
            out.append(f"{role}:날짜 수(≥{rule['min_dates']})")
        need = policy["class_min_objects"].get(role, 0)                     # [3-3] 평가할 Class가 최소한은 있어야
        for c in policy["eval_classes"]:
            if need and f"obj_{c}" in sub and sub[f"obj_{c}"].sum() < need:
                out.append(f"{role}:Class {c} 객체(≥{need})")
    band = rule.get("source_band_pp")
    if band is not None and n and abs(sub["d1"].sum() / n * 100 - overall_d1) > band:
        out.append(f"{role}:출처 비율({overall_d1:.1f}±{band}%p)")
    if role == "train" and all_strata is not None:
        lost = set(all_strata) - set(sub["stratum"])        # [3-3] Train에는 모든 층이 최소 1그룹
        if lost:
            out.append(f"train:층 누락({', '.join(sorted(lost))})")
    return out


def _train_majority(train, chosen, gt, policy) -> list:
    """[3-3] Train이 학습 데이터답게 가장 많이 가져야 하는 것
       - eval Class마다 Train 객체 수 ≥ 다른 어떤 split의 객체 수
       - 배경(빈 라벨) 이미지의 일정 비율 이상"""
    out = []
    for c in (policy["eval_classes"] if policy["train_majority"] else []):
        k = f"obj_{c}"
        if k not in gt:
            continue
        others = max((gt.loc[list(ids), k].sum() for ids in chosen.values()), default=0)
        if train[k].sum() < others:
            out.append(f"train:Class {c} 객체가 다른 split보다 적음")
    tot_bg = gt["bg_images"].sum()
    if tot_bg and train["bg_images"].sum() / tot_bg < policy["train_min_background_share"]:
        out.append(f"train:배경 이미지 {policy['train_min_background_share']:.0%} 미만")
    return out


def _assign_once(gt, overall_d1, policy, log) -> dict:
    prot = _protected(gt, policy, log)
    tot = gt["n_images"].sum()
    scene_cols = [c for c in gt if c.startswith("scene_n:")]
    class_cols = [f"obj_{c}" for c in policy["eval_classes"] if f"obj_{c}" in gt and gt[f"obj_{c}"].sum()]
    ref = {                                                                  # [3-1] 전체 구성 (기준)
        "stratum": gt.groupby("stratum")["n_images"].sum() / tot,
        "scene_cols": scene_cols, "scene": _profile(gt, scene_cols),
        "class_cols": class_cols, "class": _profile(gt, class_cols) if class_cols else None,
        "bg": gt["bg_images"].sum() / tot,
    }
    log.append("[3-1] 층: " + ", ".join(f"{s} {p:.0%}" for s, p in ref["stratum"].items()))
    log.append("[3-1] 장면(이미지 기준): " + ", ".join(f"{k.split(':')[1]} {v:.1%}" for k, v in ref["scene"].items()))
    if class_cols:
        log.append("[3-1] Class 객체 비율: " + ", ".join(f"{k[4:]} {v:.0%}" for k, v in ref["class"].items()))
    fail = Counter()          # 후보 단계에서 걸러진 조건 (장수 등, 많이 나오는 게 정상)
    block = Counter()         # 배정 전체를 막은 조건 (Train Class·배경·출처·층 누락) ← 진짜 원인

    def candidates(role, used):
        pool = [g for g in gt.index if g not in prot and g not in used]
        hi = policy["sizes"][role] + policy["size_tolerance"]
        out = []
        for k in range(1, min(policy["max_groups_per_role"], len(pool)) + 1):
            for combo in itertools.combinations(pool, k):
                if gt.loc[list(combo), "n_images"].sum() > hi:
                    continue
                sub = gt.loc[list(combo)]
                f = _check(role, sub, overall_d1, policy)
                if f:
                    fail.update(f)
                else:
                    out.append((_score(sub, ref, policy)["total"], combo))
        out.sort()
        return out[:policy["max_candidates_per_role"]]                      # 전체와 비슷한 순

    cand_cache = {}

    def cands(role, used):
        key = (role, frozenset(used))
        if key not in cand_cache:
            cand_cache[key] = candidates(role, used)
        return cand_cache[key]

    best = {"score": float("inf"), "chosen": None}

    def search(i, used, chosen, acc):
        """[3-3] 세 split 점수 합이 가장 작은 배정 찾기 (분기 한정: 이미 찾은 최선보다 나빠지면 중단)"""
        rest = gt.loc[[g for g in gt.index if g not in used]]
        if chosen:                                                          # 가지치기: 남은 것을 다 Train에
            pf = _train_majority(rest, chosen, gt, policy)                  #  줘도 안 되면 더 볼 필요 없음
            if pf:
                block.update(pf)
                return
        if i == len(ASSIGN_ORDER):
            f = _check("train", rest, overall_d1, policy, all_strata=ref["stratum"].index)
            f += _train_majority(rest, chosen, gt, policy)
            block.update(f)
            if not f and acc < best["score"]:
                best.update(score=acc, chosen=chosen)
            return
        for sc, combo in cands(ASSIGN_ORDER[i], used):
            if acc + sc >= best["score"]:                                   # 후보는 점수순 → 뒤는 더 나쁨
                break
            search(i + 1, used | set(combo), {**chosen, ASSIGN_ORDER[i]: combo}, acc + sc)

    search(0, set(), {}, 0.0)
    chosen = best["chosen"]
    if chosen is None:
        why = ", ".join(f"{k} {v}회" for k, v in block.most_common(5))
        top = ", ".join(f"{k} {v}회" for k, v in fail.most_common(4)) or "후보 없음"
        raise SplitError(f"[3-3] 조건을 만족하는 배정이 없습니다. 막힌 조건: "
                         f"{why or '역할별 후보 조합이 부족'} | 후보 단계: {top}\n"
                         "→ POLICY의 class_min_objects / train_min_background_share / role_rules 를 완화해 보세요")
    log.append(f"[3-3] 세 split 점수 합 {best['score']:.2f} (가장 작은 배정)")
    role = {g: "train" for g in gt.index}
    for r, combo in chosen.items():
        role.update({g: r for g in combo})
        sc = _score(gt.loc[list(combo)], ref, policy)
        log.append(f"[3-3] {r}: {', '.join(combo)} (차이 합 {sc['total']:.2f} · 층 {sc['stratum']:.2f} · "
                   f"장면 {sc['scene']:.2f} · Class {sc['class']:.2f} · 배경 {sc['background']:.2f})")
    return role


def step3_assign(gt, overall_d1, policy, log, issues) -> dict:
    """[3-3] 모든 조건으로 먼저 시도 → 안 되면 relax_steps 순서로 조건을 하나씩 풀어 다시 시도"""
    pol = copy.deepcopy(policy)
    errors = []
    print("  … [3단계] 조합 탐색 중 (보통 10초~1분, 조건을 완화하면 더 걸림)", flush=True)
    for step in [None] + list(policy["relax_steps"]):
        if step is not None:
            key, value, label = step
            pol[key] = value
            log.append(f"[3-3] 조건 완화: {label}")
            print(f"  … 조건을 만족하는 배정이 없어 완화: {label}", flush=True)
        try:
            role = _assign_once(gt, overall_d1, pol, log)
        except SplitError as e:
            errors.append(str(e).splitlines()[0])
            continue
        if step is not None:
            relaxed = [lbl for k, v, lbl in policy["relax_steps"][: policy["relax_steps"].index(step) + 1]]
            issues.append("[3-3] 모든 조건을 만족하는 배정이 없어 완화한 조건: " + " / ".join(relaxed)
                          + "  (완화 전 막힌 조건: " + errors[0].split("막힌 조건: ")[-1] + ")")
        return role
    raise SplitError("[3-3] 조건을 완화해도 배정이 없습니다.\n  " + "\n  ".join(errors) +
                     "\n→ 장수(size_tolerance)·날짜(min_dates)·애매한 라벨·출처 비율(source_band_pp)을 검토하세요")


# =====================================================================
# [4단계] 검증
# =====================================================================
def step4_validate(df, policy, has_labels):
    col = policy["columns"]
    # [4-1] 그룹이 여러 split에 걸치지 않는지
    mixed = df.groupby("group_id")["split"].nunique()
    mixed_t = df.groupby("time_group")["split"].nunique()
    results = [
        ("모든 이미지가 하나의 split에만 속함", bool(df["split"].isin(SPLITS).all()), ""),
        ("같은 group_id가 여러 split에 걸치지 않음", bool((mixed == 1).all()), f"{mixed[mixed > 1].index.tolist()}"),
        ("같은 time_group이 여러 split에 걸치지 않음", bool((mixed_t == 1).all()), f"{mixed_t[mixed_t > 1].index.tolist()}"),
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
        for k, v in d.drop_duplicates("group_id")["stratum"].value_counts().items():
            row[f"stratum:{k}"] = int(v)
        if has_labels:
            obj = Counter(c for cl in d["_classes"] for c in cl)
            for c in sorted(obj, key=int):
                row[f"class:{c}"] = obj[c]
        rows.append(row)
    dist = pd.DataFrame(rows).fillna(0)
    for c in dist.columns:
        if c.startswith(("scene:", "stratum:", "class:")):
            dist[c] = dist[c].astype(int)
    warn = []
    if has_labels:
        for s in ("val", "test"):
            r = dist.set_index("split").loc[s]
            warn += [f"[4-2] Class {c}가 {s}에 없음" for c in policy["eval_classes"] if r.get(f"class:{c}", 0) == 0]
    return results, dist, warn


# =====================================================================
# [5단계] 결과 파일 저장 — manifests/ (산출물 1)
#   manifests/split_manifest.csv  전체 900장 + split 열
#   manifests/train.csv / val.csv / test.csv / bridge_holdout.csv  split별로 나눈 같은 형식의 표
# =====================================================================
KEY_COLS = ["image_name", "split", "group_id", "time_group", "capture_time", "delta_t",
            "stratum", "eval_exclude", "label_ambiguous", "is_background",
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
    """[5-2] manifests/ 5개 파일 저장 → [5-3] 다시 읽어서 확인"""
    man = project_root / "manifests"
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
        res.append((f"manifests/{s}.csv 저장 ({want}장)", len(part) == want, f"{len(part)}장"))
    union = set().union(*names.values())
    overlap = sum(len(names[a] & names[b]) for a, b in itertools.combinations(SPLITS, 2))
    res.append(("split_manifest.csv = 네 파일의 합 (겹침 없음)",
                len(full) == len(union) == len(df) and overlap == 0,
                f"전체 {len(full)} / 합집합 {len(union)} / 겹침 {overlap}"))
    return res


# =====================================================================
# [6단계] (선택) YOLO 폴더로 복사 — data/yolo/, data/bridge_holdout/, configs/dataset.yaml
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
    y = project_root / ex["dataset_yaml"]            # [6-4] dataset.yaml (Bridge 제외)
    y.parent.mkdir(parents=True, exist_ok=True)
    names = "\n".join(f"  {k}: {v}" for k, v in sorted(ex["class_names"].items()))
    y.write_text(f"# {policy['name']} · Bridge Holdout 제외\npath: {yolo.resolve().as_posix()}\n"
                 f"train: images/train\nval: images/val\ntest: images/test\nnames:\n{names}\n", encoding="utf-8")
    return res


# =====================================================================
# 기록 — reports/dataset_summary.csv, reports/split_report.md
# =====================================================================
def write_reports(df, gt, dist, results, issues, log, meta, project_root: Path, policy):
    rep = project_root / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    dist.to_csv(rep / "dataset_summary.csv", index=False, encoding="utf-8-sig")
    sha = hashlib.sha256((project_root / "manifests" / "split_manifest.csv").read_bytes()).hexdigest()
    g = gt.reset_index()[["group_id", "n_images", "scene_mode", "diversity", "has_rare",
                          "n_objects", "empty_ratio", "d1", "ambiguous", "stratum", "split"]]
    g.insert(2, "dates", gt["dates"].map(",".join).values)
    mark = lambda ok: "✅" if ok else "❌"
    (rep / "split_report.md").write_text("\n".join([
        "# Split 기록 (MVP: 그룹 단위 층화 배정)", "",
        f"- Dataset Version: {meta['dataset_version']} · 정책: {policy['name']} · gap {meta['gap']}s · seed {meta['seed']}(기록용)",
        f"- 산출물 1: manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv",
        f"- split_manifest.csv SHA256: `{sha}`", "",
        "## [2단계] 그룹 속성 / [3단계] 배정", "", g.to_markdown(index=False), "",
        "## [4단계] split별 분포", "", dist.to_markdown(index=False), "",
        "## 검증", "", *[f"- {mark(ok)} {n}" + ("" if ok else f" — {d}") for n, ok, d in results], "",
        "## 확인 필요", "", *([f"- {x}" for x in issues] or ["- 없음"]), "",
        "## 실행 로그", "", *[f"- {x}" for x in log]]) + "\n", encoding="utf-8")


# =====================================================================
# 진입점
# =====================================================================
def build_split(manifest_path, data_root=None, project_root=".", dataset_version="TODO",
                gap_seconds=300, seed=42, expected_total=900, save=False, copy_images=None,
                policy=None, **_):
    """반환 (df, issues). df.attrs에 groups / distribution / results / log 저장

    save        : True면 manifests/ 5개 파일 + reports/ 저장  ([5단계])
    copy_images : True면 data/yolo/, data/bridge_holdout/로 이미지·라벨 복사 ([6단계])
                  None이면 save와 같은 값
    """
    policy = _merge(DEFAULT_POLICY, policy)
    project_root = Path(project_root)
    data_root = Path(data_root) if data_root and Path(data_root).exists() else None
    copy_images = save if copy_images is None else copy_images
    issues, log = [], []

    df = load(Path(manifest_path), data_root, policy, expected_total)
    has_labels = bool(df["has_label_file"].any())
    if not has_labels:
        issues.append("라벨 파일이 없어 클래스 다양성·희소 클래스를 계산하지 못함 (diversity=unknown)")

    df = step1_make_groups(df, gap_seconds, policy, issues, log)                   # [1단계]
    gt = step2_group_attributes(df, policy, has_labels)                            # [2단계]
    df["stratum"] = df["group_id"].map(gt["stratum"])
    role = step3_assign(gt, df["_d1"].mean() * 100, policy, log, issues)                    # [3단계]
    df["split"] = df["group_id"].map(role)
    gt["split"] = gt.index.map(role)
    df["eval_exclude"] = df["label_ambiguous"] & df["split"].isin(["test", "bridge_holdout"])
    if df["eval_exclude"].any():
        issues.append("Test·Bridge의 애매한 라벨 → eval_exclude=True: "
                      + ", ".join(df.loc[df["eval_exclude"], policy["columns"]["image_id"]]))
    results, dist, warn = step4_validate(df, policy, has_labels)                    # [4단계]
    issues += warn
    df["dataset_version"], df["policy_version"] = dataset_version, policy["name"]
    _yolo_paths(df, project_root, policy)                                          # [5-1]

    if save:
        results += step5_save_manifests(df, project_root, policy)                  # [5단계]
        log.append("[5단계] manifests/ 저장: split_manifest.csv, train/val/test/bridge_holdout.csv")
    if copy_images:
        results += step6_copy_yolo(df, data_root, project_root, policy, issues)    # [6단계]
    if save:
        write_reports(df, gt, dist, results, issues, log,
                      {"dataset_version": dataset_version, "gap": gap_seconds, "seed": seed},
                      project_root, policy)
    issues += [f"검증 실패: {n} — {d}" for n, ok, d in results if not ok]
    df.attrs.update(groups=gt, distribution=dist, results=results, log=log)
    return df, issues