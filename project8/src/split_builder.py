"""
split_builder.py — 교과 8 Split MVP (그룹 단위 층화 배정)

  [1단계] 누수 방지 그룹 만들기 (아래에서 위로 합침)
      1-1 촬영 시각 순 정렬
      1-2 인접 간격 Δt > 기준값이면 새 그룹 → time_group
      1-3 (선택) 해시 유사도가 높은 이미지가 있는 그룹끼리 병합 → group_id
      1-4 그룹 크기 분포 확인
      1-5 같은 위치·다른 이물 체크: 박스 위치(IoU)는 같은데 Class가 다른 사진 쌍 → merge(묶음 합침) 또는 flag(표시)
  [2단계] 그룹 속성 계산 (이미지 한 장이 아니라 그룹 기준)
      2-1 scene_type 최빈값      2-2 클래스 합집합 → 다양성 구간 0 / 1-2 / 3-4 / 5-6
      2-3 희소 클래스 포함 여부   2-4 객체 수, 빈 라벨 비율 (+ 출처 비율, 애매한 라벨 수)
      2-4a bbox 크기 집계 (학습 해상도 기준 small / medium / large)   2-4b 사진당 small 최대 개수
  [3단계] group_id 단위 층화 배정 (bridge_holdout → test → val → train)
      3-1 층(stratum) = scene_type 최빈값 × 클래스 다양성 구간
      3-2 Train 보호 그룹 (층에 그룹이 하나뿐 / 희소 클래스가 몰린 그룹)
      3-3 조합 탐색: 장수를 정확히 맞추고, Bridge·Test·Val 점수 합이 가장 작은 배정 선택
          점수 = 층 + 장면(이미지 수) + Class 객체 비율 + 배경 비율 차이
          필수 = Train의 Class별 객체 수가 가장 많음 · 배경 절반 이상 Train · Val/Test Class 최소 개수
      3-0 (기본) Val 먼저: original_split=validation 사진만으로 Val 75장 구성 → 그다음 Bridge·Test·Train
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
import os
import re
import shutil
from collections import Counter
from pathlib import Path

import pandas as pd

SPLITS = ["train", "val", "test", "bridge_holdout"]
ASSIGN_ORDER = ["bridge_holdout", "test", "val"]       # train = 나머지

# 교과 7 Class 번호·이름 (README 4장 · 번호 변경 금지) — dataset.yaml names
CLASS_NAMES = {0: "leaf_paper", 1: "plastic_stone_metal", 2: "branch", 3: "insect",
               4: "rubber_glove_unused", 5: "disease_browning", 6: "green_onion_pepper"}

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
    # [1-5] 같은 위치·다른 이물: 다른 묶음인데 박스 위치는 같고 이물(Class)만 바뀐 사진 쌍
    #   merge = 두 묶음을 합쳐 같은 split으로 (누수 차단) / flag = 합치지 않고 표시만 (4-7 점검용)
    #   min_boxes      : 박스가 1개인 사진은 가운데 놓기만 해도 겹쳐서 증거가 약함 → 2개 이상만 비교
    #   min_iou        : 박스 위치 평균 IoU 기준
    #   min_pair_share : 쌍에 걸린 사진이 작은 묶음의 이 비율 이상일 때만 묶음을 합침 (우연한 겹침 무시)
    "scene_pair": {"enabled": True, "mode": "merge", "min_boxes": 2, "min_iou": 0.8,
                   "min_pair_share": 0.2},                               # TODO(기준선)
    # [2단계]
    "rare_classes": ["6"],                               # [2-3] 희소 클래스
    "eval_classes": ["0", "1", "2", "3", "5"],
    # [2-4a] bbox 크기 구간: 학습 해상도(긴 변 train_px)로 줄였을 때 넓이(px²) 기준
    #   mode="quantile": 우리 데이터 전체 bbox 넓이의 1/3·2/3 지점을 경계로 → small/medium/large가 1/3씩
    #                    (COCO 32²/96²는 이 데이터엔 너무 커서 large 0%, Class 3은 100% small이 나옴)
    #   mode="fixed"   : small·large 값(px, 한 변 기준) 그대로 사용 (COCO 기준 32 / 96)
    #   mode="class_quantile": Class마다 따로 1/3·2/3 지점 (Class 5처럼 원래 작은 이물이 전부 small이 되는 문제 해결)
    "size_bins": {"mode": "class_quantile", "q": [1 / 3, 2 / 3], "train_px": 640, "small": 32, "large": 96},
    "size_check": True,                                  # [3-3a] Val·Test에서 Class별 크기 쏠림 금지
    "size_max_bin_share": 0.9,                           # [3-3a] 한 크기 구간이 90% 넘으면 쏠림
    "size_min_objects": 10,                              # [3-3a] 객체가 이보다 적은 Class는 쏠림 판정 안 함
    "small_concentration": {"top_k": 5, "share": 0.5},   # [4-6] small 상위 5장이 split small의 50% 이상이면 경고
    "ambiguous_keywords": ["모호", "ambiguous", "불확실", "의심", "REVIEW"],
    "source_d1": "이물검출_학습데이터1",
    # [3단계]
    "sizes": {"bridge_holdout": 150, "test": 75, "val": 75},   # train = 나머지 (600)
    "size_tolerance": 0,                                 # 0 = 장수 정확히
    "rare_protect_share": 0.4,
    "object_only_pin_share": 0.5,                        # [3-2] 이물만 사진이 절반 이상인 묶음 → Train                           # [3-2] 희소 클래스 이미지의 40% 이상 가진 그룹 → Train
    "pinned_train": [],                                  # [3-2] 직접 고정할 group_id (예: ["G17"])
    "pinned_val": ["scene:normal_kimchi"],               # "scene:장면" = 최빈 장면이 그 장면인 묶음 전부 (gap을 바꿔도 번호와 무관)
    "_pinned_val_note": "",                               # [3-2] Val에 '묶음째' 고정 (T02 = 정상 김치 9 + 이물만 1) → 누수 없음
    "role_rules": {                                      # [3-3] 역할별 필수 조건
        "bridge_holdout": {"max_ambiguous": 1, "min_dates": 2, "source_band_pp": 10},
        "test":           {"max_ambiguous": 1, "min_dates": 2, "source_band_pp": 10},
        "val":            {"max_ambiguous": 1, "min_dates": 1, "source_band_pp": None},
        "train":          {"source_band_pp": 10},
    },
    "max_groups_per_role": 6,
    "max_candidates_per_role": 300,                      # 역할마다 점수 좋은 후보 몇 개까지 볼지 (속도)
    # [3-3] 점수 = 전체 구성과의 차이 (작을수록 좋음)
    "score_weights": {"stratum": 0.5, "scene": 1.0, "class": 3.0, "background": 1.0, "size": 2.0},  # 크기 쏠림 해결 위해 2배
    # [3-4] 기존 original_split=validation 우선: Val을 고를 때, 기존 validation 비율이 높은 '묶음'에 가산점
    #       (사진 단위로 가져오면 같은 묶음이 Train·Val로 갈라져 누수 → 묶음 단위로만 반영)
    "orig_val_preference": {"enabled": True, "weight": 2.0},    # 묶음 단위로만 반영 → 누수 없음
    # [1-5] 기존 validation '연속 구간' → 따로 떼서 Val에 먼저 배정
    #       (예: T17 이물만 150장 중 마지막 30장이 연속으로 validation)
    #       min_run 장 이상 연속일 때만 떼고, take 장만 가져간다 (장수를 정확히 맞추기 위해 끝에서부터)
    #       ※ 같은 촬영 묶음(같은 이물 세트)을 나누는 예외 → 해당 사진은 same_bundle_split=True 로 표시
    #   take_range: 떼어 낼 장수를 이 범위에서 모두 시도해, Val 75장이 묶음째로 딱 맞는 것 중 점수가 가장 좋은 것 선택
    #   (실데이터: T17 이물만 150장 중 마지막 30장이 연속 validation → 이물만 장면을 Val에 넣는 유일한 방법)
    "orig_val_block": {"enabled": True, "min_run": 20, "take": None, "take_range": [15, 30],
                       "take_step": 5},                     # 5장 단위로만 시도 (속도)
    # [3-0] Val 먼저: original_split=validation 사진만으로 Val을 만든다 (1차 기준)
    #   - 묶음마다 기존 validation 사진을 'V 조각'으로 모으고, 조각 조합으로 Val 장수를 맞춘다
    #   - 조각을 내준 묶음의 나머지는 Train에 둔다 (Test·Bridge가 Val과 같은 이물 세트를 갖지 않게)
    #   - Bridge·Test는 손대지 않은 묶음에서 묶음째로 고른다
    #   ※ 같은 묶음이 Train·Val로 나뉘므로 Val 점수는 실제보다 좋게 나올 수 있음 (same_bundle_split=True)
    "val_first": {"enabled": False, "max_parts": 6, "top_k": 60, "touch_penalty": 0.05},   # 묶음을 쪼개므로 기본 끔 (누수)
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
        ("size_check", False, "Val·Test Class별 bbox 크기 쏠림"),          # 크기 쏠림은 마지막에 완화
    ],
    # (저장)
    "export": {"yolo_dir": "data/yolo", "bridge_dir": "data/bridge_holdout",
               "dataset_yaml": "configs/dataset.yaml",
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


SIZE_BINS = ["small", "medium", "large"]


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
    # [1-5] 같은 위치·다른 이물 체크 (장면을 외우는지)
    pairs = _scene_pairs(df, find, policy) if policy["scene_pair"]["enabled"] else []
    df["scene_pair"] = ""
    if pairs:
        name = policy["columns"]["image_id"]
        for a, b, *_ in pairs:
            for x, y in ((a, b), (b, a)):
                cur = df.at[x, "scene_pair"]
                df.at[x, "scene_pair"] = (cur + ";" if cur else "") + str(df.at[y, name])
        tg_pairs = sorted({tuple(sorted((df.at[a, "time_group"], df.at[b, "time_group"]))) for a, b, *_ in pairs})
        log.append(f"[1-5] 같은 위치·다른 이물 쌍 {len(pairs)}개 (묶음 쌍 {len(tg_pairs)}개)")
        if policy["scene_pair"]["mode"] == "merge":
            size = df["time_group"].value_counts()
            hit = {}                                   # 묶음 쌍마다 쌍에 걸린 사진 수 (작은 묶음 기준)
            for a, b, *_ in pairs:
                k = tuple(sorted((df.at[a, "time_group"], df.at[b, "time_group"])))
                hit.setdefault(k, (set(), set()))
                hit[k][0].add(a); hit[k][1].add(b)
            for (ga, gb), (sa, sb_) in hit.items():
                share = max(len(sa), len(sb_)) / min(size[ga], size[gb])
                if share >= policy["scene_pair"]["min_pair_share"] and union(ga, gb):
                    issues.append(f"[1-5] 같은 위치·다른 이물 → {ga} + {gb} 병합 (작은 묶음의 {share:.0%})")
        else:
            issues.append(f"[1-5] 같은 위치·다른 이물 쌍 {len(pairs)}개 표시만 함 (flag) → 4-7에서 split별 점검")
    df.attrs["scene_pairs"] = pairs

    members = {}
    for g in df["time_group"].unique():
        members.setdefault(find(g), []).append(g)
    gid = {g: "+".join(ms) for ms in members.values() for g in ms}
    df["group_id"] = df["time_group"].map(gid)

    # [1-5] 기존 validation 연속 구간 떼어내기 (Val 우선 후보)
    df["orig_val_block"] = False
    ob = policy["orig_val_block"]
    if ob["enabled"] and "original_split" in df:
        is_v = df["original_split"].astype(str).str.lower().isin(["val", "valid", "validation"])
        run_id = (is_v != is_v.shift()).cumsum()
        for _, idx in df[is_v].groupby(run_id[is_v]).groups.items():
            idx = list(idx)
            if len(idx) < ob["min_run"]:
                continue
            take = idx[-ob["take"]:] if ob.get("take") else idx    # 끝에서부터 take장 (나머지는 원래 묶음에 남음)
            src = df.at[take[0], "group_id"]
            df.loc[take, "group_id"] = f"{src}_V"
            df.loc[take, "orig_val_block"] = True
            log.append(f"[1-5] 기존 validation 연속 {len(idx)}장 발견 ({src}) → 끝의 {len(take)}장을 "
                       f"'{src}_V' 그룹으로 떼어 Val 우선 배정")
            issues.append(f"[1-5] {src}_V {len(take)}장은 {src}와 같은 촬영 묶음(같은 이물 세트) → "
                          "Val 점수가 실제보다 좋게 나올 수 있음 (same_bundle_split=True로 표시)")
    df["same_bundle_split"] = df["orig_val_block"]
    log.append(f"[1-3] group_id {df['group_id'].nunique()}개")

    # [1-4] 그룹 크기 분포 확인
    size = df["group_id"].value_counts()
    log.append(f"[1-4] 그룹 크기: 최소 {size.min()} · 중앙값 {int(size.median())} · 최대 {size.max()}장")
    for g, n in size[size > len(df) * policy["max_group_share"]].items():
        issues.append(f"[1-4] 그룹 {g}가 너무 큼: {n}장 ({n / len(df):.0%})")
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
            "orig_val": int(d["original_split"].astype(str).str.lower()                # [2-5] 기존 validation 수
                            .isin(["val", "valid", "validation"]).sum()) if "original_split" in d else 0,
            "ambiguous": int(d["label_ambiguous"].sum()),
            "dates": tuple(sorted(d["capture_date"].unique())),
            "first_time": d["capture_time"].min(),
            "orig_block": bool(d["orig_val_block"].all()),
        }
        for s_ in scenes:                                                    # [2-1] 장면별 이미지 수 (최빈값만 보면
            row[f"scene_n:{s_}"] = int(sc.get(s_, 0))                        #  T03처럼 섞인 그룹의 배경을 놓침)
        for c in sorted(set(obj) | set(policy["eval_classes"]) | set(policy["rare_classes"]), key=int):
            row[f"obj_{c}"], row[f"img_{c}"] = obj.get(c, 0), img.get(c, 0)
        size = Counter(f"{c}_{z}" for zs in d["_sizes"] for c, z in zs)      # [2-4a] Class × 크기 구간
        for c in policy["eval_classes"]:
            for z in SIZE_BINS:
                row[f"sz_{c}_{z}"] = size.get(f"{c}_{z}", 0)
        row["max_small_img"] = int(d["n_small"].max()) if len(d) else 0     # [2-4b] 사진당 small 최대
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
    for g in gt.index:                                                       # 이물만 묶음 본체는 Train
        if not gt.at[g, "orig_block"] and g not in prot and \
                gt.at[g, "scene_n:object_only"] / gt.at[g, "n_images"] >= policy["object_only_pin_share"] \
                if "scene_n:object_only" in gt else False:
            prot[g] = "이물만(object_only) 묶음 → Train에도 이물만 사진이 있어야 함"
    free = ~gt["orig_block"] & ~gt.index.isin(policy.get("pinned_val", []))   # Val 고정 묶음은 보호 대상 아님
    counts = gt.loc[free, "stratum"].value_counts()
    for g, s in gt.loc[free, "stratum"].items():
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


def _score(sub, ref, policy, role=None) -> dict:
    """[3-3] 전체와 얼마나 다른가 (0 = 전체와 같음). 항목별 L1 거리 × 가중치
       role == "val" 이면 기존 validation 비율이 높은 묶음 조합에 가산점 (점수를 낮춤)"""
    w = policy["score_weights"]
    parts = {
        "stratum": float((sub.groupby("stratum")["n_images"].sum() / sub["n_images"].sum())
                         .reindex(ref["stratum"].index, fill_value=0).sub(ref["stratum"]).abs().sum()),
        "scene": float(_profile(sub, ref["scene_cols"]).sub(ref["scene"]).abs().sum()),
        "class": float(_profile(sub, ref["class_cols"]).sub(ref["class"]).abs().sum()) if ref["class_cols"] else 0.0,
        "background": abs(sub["bg_images"].sum() / sub["n_images"].sum() - ref["bg"]) * 10,
        "size": _size_diff(sub, ref),                                     # [3-4] Class별 크기 분포 차이
    }
    parts["total"] = sum(parts[k] * w[k] for k in w)
    ov = policy["orig_val_preference"]
    if role == "val" and ov["enabled"]:                                     # [3-4] 기존 validation 우선
        share = sub["orig_val"].sum() / sub["n_images"].sum()
        parts["orig_val_share"] = round(share, 3)
        parts["total"] += ov["weight"] * (1 - share)                     # 비율이 높을수록 벌점이 작음
                                                                        # (점수가 0 이상이어야 탐색의 가지치기가 맞음)
    return parts


def _size_profile(sub, c):
    """Class c의 small / medium / large 비율. 객체가 없으면 None"""
    v = pd.Series({z: sub[f"sz_{c}_{z}"].sum() for z in SIZE_BINS if f"sz_{c}_{z}" in sub})
    return v / v.sum() if len(v) and v.sum() else None


def _size_diff(sub, ref) -> float:
    """[3-4] Class마다 (크기 구간 비율 L1 차이 × 그 Class 비중)의 합. 객체가 없는 Class는 건너뜀
    (Class가 아예 없는 문제는 class 점수가 맡음)"""
    tot = 0.0
    for c, (prof, w) in ref.get("size", {}).items():
        p = _size_profile(sub, c)
        if p is not None:
            tot += w * float(p.sub(prof).abs().sum())
    return tot


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
        if policy["size_check"] and role in ("val", "test"):               # [3-3a] 크기 쏠림 금지
            for c in policy["eval_classes"]:
                cols = [f"sz_{c}_{z}" for z in SIZE_BINS if f"sz_{c}_{z}" in sub]
                n_c = sub[cols].sum().sum() if cols else 0
                if n_c >= policy["size_min_objects"] and \
                        sub[cols].sum().max() / n_c > policy["size_max_bin_share"]:
                    out.append(f"{role}:Class {c} 크기 쏠림(>{policy['size_max_bin_share']:.0%})")
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


def _make_ref(gt, policy):
    tot = gt["n_images"].sum()
    scene_cols = [c for c in gt if c.startswith("scene_n:")]
    class_cols = [f"obj_{c}" for c in policy["eval_classes"] if f"obj_{c}" in gt and gt[f"obj_{c}"].sum()]
    return {"stratum": gt.groupby("stratum")["n_images"].sum() / tot,
            "scene_cols": scene_cols, "scene": _profile(gt, scene_cols),
            "class_cols": class_cols, "class": _profile(gt, class_cols) if class_cols else None,
            "bg": gt["bg_images"].sum() / tot,
            "size": {c: (_size_profile(gt, c), w)                            # [3-1] Class별 크기 분포 (기준)
                     for c, w in ((k[4:], v) for k, v in
                                  (_profile(gt, class_cols).items() if class_cols else []))
                     if _size_profile(gt, c) is not None}}


def _assign_once(gt, overall_d1, policy, log, order=None, fixed=None, ref=None) -> dict:
    """order : 배정할 역할 순서 (기본 bridge → test → val)
       fixed : {"val": (group…), "train": {group…}} 처럼 미리 정해진 그룹 (val_first에서 사용)
       ref   : 비교 기준(전체 구성). 주지 않으면 gt 전체로 계산"""
    order = order or ASSIGN_ORDER
    fixed = fixed or {}
    fixed_val = tuple(fixed.get("val", ()))
    prot = _protected(gt, policy, log) | set(fixed.get("train", ()))
    ref = ref or _make_ref(gt, policy)                                       # [3-1] 전체 구성 (기준)
    class_cols = ref["class_cols"]
    log.append("[3-1] 층: " + ", ".join(f"{s} {p:.0%}" for s, p in ref["stratum"].items()))
    log.append("[3-1] 장면(이미지 기준): " + ", ".join(f"{k.split(':')[1]} {v:.1%}" for k, v in ref["scene"].items()))
    if class_cols:
        log.append("[3-1] Class 객체 비율: " + ", ".join(f"{k[4:]} {v:.0%}" for k, v in ref["class"].items()))
    fail = Counter()          # 후보 단계에서 걸러진 조건 (장수 등, 많이 나오는 게 정상)
    block = Counter()         # 배정 전체를 막은 조건 (Train Class·배경·출처·층 누락) ← 진짜 원인

    blocks = tuple(g for g in gt.index if gt.at[g, "orig_block"])           # [1-5] Val 우선 블록
    blocks += tuple(g for g in policy.get("pinned_val", []) if g in gt.index and g not in blocks)  # Val 묶음째 고정
    if blocks:
        log.append(f"[3-4] 기존 validation 블록 → Val 고정: {', '.join(blocks)}")

    def candidates(role, used):
        pool = [g for g in gt.index if g not in prot and g not in used and g not in blocks
                and g not in fixed_val]
        base = blocks if role == "val" else ()
        hi = policy["sizes"][role] + policy["size_tolerance"]
        lo = policy["sizes"][role] - policy["size_tolerance"]
        out = []
        # 장수 합이 lo~hi인 조합만 만든다 (깊이 우선 + 넘치면 중단) — 묶음이 많아져도 빠르게
        n_of = gt["n_images"].to_dict()
        pool = sorted(pool, key=lambda g: n_of[g])
        start = sum(n_of[g] for g in base)
        kmax = min(policy["max_groups_per_role"], len(pool))

        def dfs(i, chosen, total):
            if lo <= total <= hi and (chosen or base):
                yield tuple(chosen)
            if len(chosen) == kmax:
                return
            for j in range(i, len(pool)):
                n = n_of[pool[j]]
                if total + n > hi:
                    break                                           # 정렬돼 있으므로 뒤는 더 큼
                chosen.append(pool[j])
                yield from dfs(j + 1, chosen, total + n)
                chosen.pop()

        for c in dfs(0, [], start):
            combo = base + c
            sub = gt.loc[list(combo)]
            f = _check(role, sub, overall_d1, policy)
            if f:
                fail.update(f)
            else:
                out.append((_score(sub, ref, policy, role)["total"], combo))
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
        if i == len(order):
            f = _check("train", rest, overall_d1, policy,
                       all_strata=gt.loc[~gt["orig_block"] & ~gt.index.isin(fixed_val)
                                         & ~gt.index.isin(policy.get("pinned_val", [])), "stratum"].unique())
            f += _train_majority(rest, chosen, gt, policy)
            block.update(f)
            if not f and acc < best["score"]:
                best.update(score=acc, chosen=chosen)
            return
        for sc, combo in cands(order[i], used):
            if acc + sc >= best["score"]:                                   # 후보는 점수순 → 뒤는 더 나쁨
                break
            search(i + 1, used | set(combo), {**chosen, order[i]: combo}, acc + sc)

    start = {"val": fixed_val} if fixed_val else {}
    search(0, set(fixed_val), start, 0.0)
    chosen = best["chosen"]
    if chosen is None:
        why = ", ".join(f"{k} {v}회" for k, v in block.most_common(5))
        top = ", ".join(f"{k} {v}회" for k, v in fail.most_common(4)) or "후보 없음"
        raise SplitError(f"[3-3] 조건을 만족하는 배정이 없습니다. 막힌 조건: "
                         f"{why or '역할별 후보 조합이 부족'} | 후보 단계: {top}\n"
                         "→ POLICY의 class_min_objects / train_min_background_share / role_rules 를 완화해 보세요")
    log.append(f"[3-3] 점수 합 {best['score']:.2f} (가장 작은 배정)")
    role_score = best["score"]
    role = {g: "train" for g in gt.index}
    for r, combo in chosen.items():
        role.update({g: r for g in combo})
        sc = _score(gt.loc[list(combo)], ref, policy, r)
        extra = f" · 기존 validation {sc['orig_val_share']:.0%}" if "orig_val_share" in sc else ""
        log.append(f"[3-3] {r}: {', '.join(combo)} (차이 합 {sc['total']:.2f} · 층 {sc['stratum']:.2f} · "
                   f"장면 {sc['scene']:.2f} · Class {sc['class']:.2f} · 배경 {sc['background']:.2f}{extra})")
    role["__score__"] = role_score
    return role


def step3_assign(gt, overall_d1, policy, log, issues, info=None) -> dict:
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
            score = role.pop("__score__", 0.0)
        except SplitError as e:
            errors.append(str(e).splitlines()[0])
            continue
        n_relax = 0 if step is None else policy["relax_steps"].index(step) + 1
        if info is not None:
            info.update(score=score, relaxed=n_relax)
        if step is not None:
            relaxed = [lbl for k, v, lbl in policy["relax_steps"][:n_relax]]
            issues.append("[3-3] 모든 조건을 만족하는 배정이 없어 완화한 조건: " + " / ".join(relaxed)
                          + "  (완화 전 막힌 조건: " + errors[0].split("막힌 조건: ")[-1] + ")")
        return role
    raise SplitError("[3-3] 조건을 완화해도 배정이 없습니다.\n  " + "\n  ".join(errors) +
                     "\n→ 장수(size_tolerance)·날짜(min_dates)·애매한 라벨·출처 비율(source_band_pp)을 검토하세요")



# =====================================================================
# [3-0] Val 먼저 — original_split=validation 사진으로 Val을 만들고, 나머지를 배정
# =====================================================================
def _val_first_once(df, overall_d1, policy, log, has_labels):
    vf = policy["val_first"]
    is_v = df["original_split"].astype(str).str.lower().isin(["val", "valid", "validation"])
    if not is_v.any():
        raise SplitError("[3-0] original_split=validation 사진이 없습니다 (val_first를 끄세요)")
    gt_full = step2_group_attributes(df, policy, has_labels)
    ref = _make_ref(gt_full, policy)                                          # 기준 = 전체 900장 구성

    # [3-0-1] 묶음별 V 조각 (기존 validation 사진만)
    dv = df[is_v].copy()
    dv["group_id"] = dv["group_id"] + "_V"
    vt = step2_group_attributes(dv, policy, has_labels)
    want, tol = policy["sizes"]["val"], policy["size_tolerance"]

    # [3-0-2] Val 후보: V 조각 조합 중 장수가 맞고 Val 조건을 통과하는 것, 구성이 고른 순
    cand = []
    parts = list(vt.index)
    for k in range(1, min(vf["max_parts"], len(parts)) + 1):
        for combo in itertools.combinations(parts, k):
            n = vt.loc[list(combo), "n_images"].sum()
            if abs(n - want) > tol:
                continue
            sub = vt.loc[list(combo)]
            if _check("val", sub, overall_d1, policy):
                continue
            sc = _score(sub, ref, policy, "val")["total"] + vf["touch_penalty"] * k   # 조각 수가 적을수록 우대
            cand.append((sc, combo))
    cand.sort()
    cand = cand[:vf["top_k"]]
    if not cand:
        raise SplitError("[3-0] 기존 validation 조각으로 Val 장수를 맞추는 조합이 없습니다 "
                         "(size_tolerance나 role_rules.val을 완화해 보세요)")

    # [3-0-3] Val 후보마다 Bridge·Test 배정 → 전체 점수가 가장 좋은 것
    best = None
    errors = Counter()
    for vsc, combo in cand:
        if best and vsc >= best[0]:
            break                                                            # 나머지 점수는 0 이상
        touched = {c[:-2] for c in combo}
        d2 = df.copy()
        in_val = d2["group_id"].isin(touched) & is_v & (d2["group_id"] + "_V").isin(combo)
        d2.loc[in_val, "group_id"] = d2.loc[in_val, "group_id"] + "_V"
        rest = d2["group_id"].isin(touched) & ~in_val
        d2.loc[rest, "group_id"] = d2.loc[rest, "group_id"] + "_R"            # 조각을 내준 묶음의 나머지
        gt2 = step2_group_attributes(d2, policy, has_labels)
        tmp_log = []
        try:
            role = _assign_once(gt2, overall_d1, policy, tmp_log,
                                order=["bridge_holdout", "test"],
                                fixed={"val": tuple(combo), "train": {f"{t}_R" for t in touched} & set(gt2.index)},
                                ref=ref)
        except SplitError as e:
            errors[str(e).split("막힌 조건: ")[-1].split(" | ")[0][:80]] += 1
            continue
        total = vsc + role.pop("__score__")
        if best is None or total < best[0]:
            best = (total, combo, d2, gt2, role, tmp_log, vsc)
    if best is None:
        raise SplitError("[3-0] Val 후보 " + str(len(cand)) + "개 모두 Bridge·Test 배정 실패. 막힌 조건: "
                         + "; ".join(f"{k} ({v}회)" for k, v in errors.most_common(3)))
    total, combo, d2, gt2, role, tmp_log, vsc = best
    for g in combo:
        role[g] = "val"
    n_orig = int(is_v.sum())
    log.append(f"[3-0] Val 먼저: 기존 validation {n_orig}장 → 묶음별 V 조각 {len(vt)}개 중 "
               f"{', '.join(combo)} 선택 ({int(vt.loc[list(combo), 'n_images'].sum())}장)")
    log.append(f"[3-0] 조각을 내준 묶음의 나머지 → Train: {', '.join(sorted(c[:-2] + '_R' for c in combo))}")
    log.extend(tmp_log)
    log.append(f"[3-3] val: {', '.join(combo)} (점수 {vsc:.2f})")
    return role, d2, gt2


def step3_val_first(df, overall_d1, policy, log, issues, has_labels):
    """[3-0] 조건 완화 사다리를 적용해 Val 먼저 배정"""
    pol = copy.deepcopy(policy)
    errors = []
    print("  … [3단계] Val 먼저(기존 validation) 배정 탐색 중 (보통 30초~2분)", flush=True)
    for step in [None] + list(policy["relax_steps"]):
        if step is not None:
            key, value, label = step
            pol[key] = value
            log.append(f"[3-3] 조건 완화: {label}")
            print(f"  … 조건을 만족하는 배정이 없어 완화: {label}", flush=True)
        try:
            role, d2, gt2 = _val_first_once(df, overall_d1, pol, log, has_labels)
        except SplitError as e:
            errors.append(str(e).splitlines()[0])
            continue
        if step is not None:
            relaxed = [lbl for k, v, lbl in policy["relax_steps"][: policy["relax_steps"].index(step) + 1]]
            issues.append("[3-3] 모든 조건을 만족하는 배정이 없어 완화한 조건: " + " / ".join(relaxed)
                          + "  (완화 전: " + errors[0][:200] + ")")
        return role, d2, gt2
    raise SplitError("[3-0] 조건을 완화해도 배정이 없습니다.\n  " + "\n  ".join(errors))


# =====================================================================
# [4단계] 검증
# =====================================================================
def step4_validate(df, policy, has_labels):
    col = policy["columns"]
    # [4-1] 그룹이 여러 split에 걸치지 않는지
    mixed = df.groupby("group_id")["split"].nunique()
    mixed_t = df[~df["same_bundle_split"]].groupby("time_group")["split"].nunique()   # 의도적 예외 제외
    results = [
        ("모든 이미지가 하나의 split에만 속함", bool(df["split"].isin(SPLITS).all()), ""),
        ("같은 group_id가 여러 split에 걸치지 않음", bool((mixed == 1).all()), f"{mixed[mixed > 1].index.tolist()}"),
        ("같은 time_group이 여러 split에 걸치지 않음 (Val 조각으로 나눈 묶음은 예외)", bool((mixed_t == 1).all()),
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
    size_dist = pd.DataFrame()
    if has_labels:
        size_dist, w2 = _size_report(df, policy)                            # [4-5] [4-6]
        warn += w2
        warn += _scene_pair_report(df, policy)                              # [4-7]
    return results, dist, warn, size_dist


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
# [5단계] 결과 파일 저장 — manifests/ (산출물 1)
#   manifests/split_manifest.csv  전체 900장 + split 열
#   manifests/train.csv / val.csv / test.csv / bridge_holdout.csv  split별로 나눈 같은 형식의 표
# =====================================================================
KEY_COLS = ["image_name", "split", "group_id", "time_group", "capture_time", "delta_t",
            "stratum", "eval_exclude", "same_bundle_split", "label_ambiguous", "is_background",
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



def _original_val_review(df) -> list:
    """(기록) 기존 original_split=validation을 Val 후보로 검토한 근거.
    배정에는 쓰지 않는다 — 사진 단위로 뽑혀 있어 그대로 쓰면 누수가 생기기 때문."""
    if "original_split" not in df:
        return []
    is_val = df["original_split"].astype(str).str.lower().isin(["val", "valid", "validation"])
    if not is_val.any():
        return []
    t_val = df.loc[is_val, "capture_time"].sort_values().values
    t_tr = df.loc[~is_val, "capture_time"].sort_values().values
    import numpy as np
    idx = np.searchsorted(t_tr, t_val)
    near = 0
    for v, i in zip(t_val, idx):
        gaps = [abs((v - t_tr[j]) / np.timedelta64(1, "s")) for j in (i - 1, i) if 0 <= j < len(t_tr)]
        near += bool(gaps) and min(gaps) <= 60
    g = (df.assign(_v=is_val).groupby("time_group")
           .agg(장수=("_v", "size"), 기존_validation=("_v", "sum")))
    g["비율(%)"] = (g["기존_validation"] / g["장수"] * 100).round(0).astype(int)
    g["배정된 split"] = df.groupby("time_group")["split"].first()
    return [
        "## 기존 validation 검토", "",
        f"- 기존 validation {int(is_val.sum())}장이 촬영 묶음 {int((g['기존_validation'] > 0).sum())}개에 "
        f"{g.loc[g['기존_validation'] > 0, '비율(%)'].min()}~{g['비율(%)'].max()}%씩 흩어져 있음 "
        "(사진 단위 무작위 추출로 보임)",
        f"- 그중 {near}장은 60초 안에 기존 train 사진이 바로 옆에 있음 (같은 묶음 = 같은 이물 세트)",
        "- 사진 단위로 Val에 넣으면 같은 묶음이 Train·Val로 갈라져 누수 → 사용하지 않음",
        "- 대신 묶음 단위로 반영: Val을 고를 때 기존 validation 비율이 높은 묶음에 가산점 ([3-4] orig_val_preference)",
        "  (모든 묶음 비율이 14~30%로 비슷해 효과는 크지 않을 수 있음)",
        "", g.reset_index().pipe(_md), "",
    ]


def _md(t) -> str:
    """표 → Markdown. tabulate가 없으면 고정폭 글자 표로 대신 (실행이 멈추지 않게)"""
    try:
        return t.to_markdown(index=False)
    except ImportError:
        return "```\n" + t.to_string(index=False) + "\n```"


# =====================================================================
# 기록 — reports/dataset_summary.csv, reports/split_report.md
# =====================================================================
def write_reports(df, gt, dist, results, issues, log, meta, project_root: Path, policy):
    rep = project_root / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    dist.to_csv(rep / "dataset_summary.csv", index=False, encoding="utf-8-sig")
    size_dist = df.attrs.get("size_distribution", pd.DataFrame())
    if not size_dist.empty:
        size_dist.to_csv(rep / "size_distribution.csv", index=False, encoding="utf-8-sig")   # [4-5]
    name = policy["columns"]["image_id"]
    pd.DataFrame([{"image_a": df.at[a, name], "image_b": df.at[b, name], "iou": v,
                   "class_a": ca, "class_b": cb, "split_a": df.at[a, "split"], "split_b": df.at[b, "split"]}
                  for a, b, v, ca, cb in df.attrs.get("scene_pairs", [])],
                 columns=["image_a", "image_b", "iou", "class_a", "class_b", "split_a", "split_b"]
                 ).to_csv(rep / "scene_pairs.csv", index=False, encoding="utf-8-sig")              # [1-5]
    sha = hashlib.sha256((project_root / "manifests" / "split_manifest.csv").read_bytes()).hexdigest()
    g = gt.reset_index()[["group_id", "n_images", "scene_mode", "diversity", "has_rare",
                          "n_objects", "empty_ratio", "d1", "ambiguous", "stratum", "split"]]
    g.insert(2, "dates", gt["dates"].map(",".join).values)
    mark = lambda ok: "✅" if ok else "❌"
    orig = _original_val_review(df)
    (rep / "split_report.md").write_text("\n".join([
        "# Split 기록 (MVP: 그룹 단위 층화 배정)", "",
        f"- Dataset Version: {meta['dataset_version']} · 정책: {policy['name']} · gap {meta['gap']}s · seed {meta['seed']}(기록용)",
        f"- 산출물 1: manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv",
        f"- split_manifest.csv SHA256: `{sha}`", "",
        "## [2단계] 그룹 속성 / [3단계] 배정", "", g.pipe(_md), "",
        "## [4단계] split별 분포", "", dist.pipe(_md), "",
        "## [4-5] split × Class × bbox 크기", "",
        (size_dist.pipe(_md) if not size_dist.empty else "- 라벨 없음"), "",
        f"- 같은 위치·다른 이물 쌍: {len(df.attrs.get('scene_pairs', []))}개 (reports/scene_pairs.csv)", "",
        "## 검증", "", *[f"- {mark(ok)} {n}" + ("" if ok else f" — {d}") for n, ok, d in results], "",
        *orig,
        "## 확인 필요", "", *([f"- {x}" for x in issues] or ["- 없음"]), "",
        "## 실행 로그", "", *[f"- {x}" for x in log]]) + "\n", encoding="utf-8")


def _resolve_pinned_val(df, policy):
    """pinned_val의 "scene:장면" 항목을 실제 묶음 이름으로 바꾼다 (원래 묶음 = time_group 기준)"""
    out = []
    col = policy["columns"]["scene"]
    mode = df[~df["orig_val_block"]].groupby("group_id")[col].agg(lambda x: x.mode().iat[0])
    for g in policy["pinned_val"]:
        out += list(mode[mode == g[6:]].index) if g.startswith("scene:") else [g]
    return list(dict.fromkeys(out))


def _try_block_sizes(df0, gap_seconds, policy, issues, log, has_labels):
    """[1-5]+[3단계] 기존 validation 연속 구간(T17 끝 30장)에서 떼어 낼 장수를 take_range 안에서 모두 시도.
    Val = 고정 묶음(pinned_val) + 떼어 낸 블록 + 다른 묶음 '통째로' → 장수가 정확히 맞는 경우만 배정을 돌린다.
    완화한 조건 수가 적고, 점수가 작은 배정을 고른다."""
    lo, hi = policy["orig_val_block"]["take_range"]
    # 1) 미리 거르기: 묶음 크기 합으로 Val 75장을 맞출 수 있는 take만 (부분합)
    probe = step1_make_groups(df0.copy(), gap_seconds, _merge(policy, {"orig_val_block": {"take": hi}}), [], [])
    size = probe[~probe["orig_val_block"]].groupby("group_id").size()
    policy = _merge(policy, {})
    policy["pinned_val"] = _resolve_pinned_val(probe, policy)
    pinned = [g for g in policy["pinned_val"] if g in size]
    log.append(f"[3-2] Val 묶음째 고정: {', '.join(pinned) or '없음'}")
    blocked_src = {g[:-2] for g in probe.loc[probe["orig_val_block"], "group_id"].unique()}
    free = [n for g, n in size.items() if g not in pinned and g not in blocked_src and g not in policy["pinned_train"]]
    sums = {0}
    for n in free:
        sums |= {x + n for x in sums if x + n <= policy["sizes"]["val"]}
    need = policy["sizes"]["val"] - int(size[pinned].sum())
    step = policy["orig_val_block"].get("take_step", 1)
    takes = [t for t in range(lo, hi + 1) if need - t in sums]
    stepped = [t for t in takes if (t - lo) % step == 0]
    takes = stepped or takes[:3]
    log.append(f"[1-5] 기존 validation 블록 장수 후보 {lo}~{hi} 중 Val 75장이 묶음째로 맞는 값: {takes}")
    if not takes:
        raise SplitError("[1-5] take_range 안에서 Val 장수를 묶음째로 맞출 수 없습니다 (take_range 또는 pinned_val 조정)")
    best = None
    for t in takes:
        pol = _merge(policy, {"orig_val_block": {"take": t}})
        iss, lg, info = [], [], {}
        df = step1_make_groups(df0.copy(), gap_seconds, pol, iss, lg)
        gt = step2_group_attributes(df, pol, has_labels)
        print(f"  … [1-5] T17 블록 {t}장으로 시도", flush=True)
        try:
            role = step3_assign(gt, df["_d1"].mean() * 100, pol, lg, iss, info)
        except SplitError as e:
            log.append(f"[1-5] 블록 {t}장: 배정 실패 ({str(e).splitlines()[0][:80]})")
            continue
        key = (info["relaxed"], info["score"])
        log.append(f"[1-5] 블록 {t}장: 완화 {info['relaxed']}개 · 점수 {info['score']:.2f}")
        if best is None or key < best[0]:
            best = (key, t, df, gt, role, iss, lg)
        if best[0][0] == 0:
            break                                   # 완화 없는 배정을 이미 찾음 → 더 볼 필요 적음 (속도)
    if best is None:
        raise SplitError("[1-5] 모든 블록 장수에서 배정 실패")
    _, t, df, gt, role, iss, lg = best
    log.append(f"[1-5] 선택: 기존 validation 블록 {t}장")
    log.extend(lg)
    issues.extend(iss)
    return df, gt, role


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
    if has_labels:
        b = df.attrs.get("size_bins", {})
        log.append(f"[2-4a] bbox 크기 경계({b.get('mode')}, 학습 {policy['size_bins']['train_px']}px 기준 √넓이): "
                   f"small < {b.get('small_px')}px ≤ medium < {b.get('large_px')}px ≤ large")
    if not has_labels:
        issues.append("라벨 파일이 없어 클래스 다양성·희소 클래스를 계산하지 못함 (diversity=unknown)")

    ob = policy["orig_val_block"]
    if ob["enabled"] and ob.get("take_range") and not ob.get("take") and not policy["val_first"]["enabled"]:
        df, gt, role = _try_block_sizes(df, gap_seconds, policy, issues, log, has_labels)   # [1-5]+[3단계]
        overall_d1 = df["_d1"].mean() * 100
    else:
        df = step1_make_groups(df, gap_seconds, policy, issues, log)               # [1단계]
        overall_d1 = df["_d1"].mean() * 100
        gt = role = None
    if role is not None:
        pass
    elif policy["val_first"]["enabled"] and "original_split" in df:                # [3-0] Val 먼저
        role, df, gt = step3_val_first(df, overall_d1, policy, log, issues, has_labels)
        touched = {g[:-2] for g in gt.index if g.endswith(("_V", "_R"))}
        df["same_bundle_split"] = df["group_id"].str[:-2].isin(touched) & df["group_id"].str.endswith(("_V", "_R"))
        if df["same_bundle_split"].any():
            issues.append(f"[3-0] Val은 기존 validation 사진으로 구성 → 같은 묶음({', '.join(sorted(touched))})의 "
                          "나머지가 Train에 있어 Val 점수가 실제보다 좋게 나올 수 있음 (same_bundle_split=True)")
    else:
        gt = step2_group_attributes(df, policy, has_labels)                        # [2단계]
        role = step3_assign(gt, overall_d1, policy, log, issues)                    # [3단계]
    df["stratum"] = df["group_id"].map(gt["stratum"])
    df["split"] = df["group_id"].map(role)
    gt["split"] = gt.index.map(role)
    df["eval_exclude"] = df["label_ambiguous"] & df["split"].isin(["test", "bridge_holdout"])
    if df["eval_exclude"].any():
        issues.append("Test·Bridge의 애매한 라벨 → eval_exclude=True: "
                      + ", ".join(df.loc[df["eval_exclude"], policy["columns"]["image_id"]]))
    pairs = df.attrs.get("scene_pairs", [])
    results, dist, warn, size_dist = step4_validate(df, policy, has_labels)        # [4단계]
    df.attrs["size_distribution"] = size_dist
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
    df.attrs.update(groups=gt, distribution=dist, results=results, log=log,
                    size_distribution=size_dist, scene_pairs=pairs)
    return df, issues