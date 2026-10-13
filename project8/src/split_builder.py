"""
split_builder.py
교과 7 FINAL 900장을 Train / Val / Frozen Test / Bridge Holdout 네 역할로 확정한다.

입력 : manifests/manifest_final.csv (교과 7 Master Manifest)
출력 : manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
       reports/dataset_summary.csv

처리 순서 (가이드 예시 3의 4번)
  ① Manifest 읽기·확인          load_manifest()
  ② 유사 촬영 그룹 만들기        make_capture_group()
  ③ Split 정책 적용             assign_splits()
  ④ 성공 기준 검사              validate_splits()
  ⑤ 분포 요약·저장              build_summary(), save_outputs()
"""
from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

import pandas as pd

SPLITS = ["train", "val", "test", "bridge_holdout"]
REQUIRED_COLUMNS = [
    "relative_path",
    "label_relative_path",
    "image_name",
    "source_dataset",
    "original_split",
    "scene_type",
]
NUM_CLASSES = 7          # 교과 7 Class ID 0~6 유지
UNUSED_CLASSES = {4}     # 고무장갑: 사용하지 않음


# ------------------------------------------------------------------
# ① Manifest 읽기·확인
# ------------------------------------------------------------------
def load_manifest(manifest_path: Path) -> pd.DataFrame:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest를 찾을 수 없습니다: {manifest_path}")

    df = pd.read_csv(manifest_path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Manifest에 필요한 컬럼이 없습니다: {missing}")

    dup = df["relative_path"].duplicated()
    if dup.any():
        raise ValueError(f"relative_path 중복: {df.loc[dup, 'relative_path'].tolist()[:5]}")

    return df


# ------------------------------------------------------------------
# ② 유사 촬영 그룹 (capture_group)
#    파일명 = 촬영 시각 (예: 250410_144403911987 → 2025-04-10 14:44:03)
#    시간순 정렬 후, 앞 사진과 gap_seconds 넘게 벌어지면 새 그룹
# ------------------------------------------------------------------
def make_capture_group(df: pd.DataFrame, gap_seconds: int) -> pd.DataFrame:
    df = df.copy()
    df["capture_time"] = pd.to_datetime(
        df["image_name"].str[:13], format="%y%m%d_%H%M%S", errors="coerce"
    )
    bad = df["capture_time"].isna()
    if bad.any():
        raise ValueError(f"파일명에서 촬영시각을 읽지 못함: {df.loc[bad, 'image_name'].tolist()[:5]}")

    df = df.sort_values("capture_time").reset_index(drop=True)
    gap = df["capture_time"].diff().dt.total_seconds()
    group_no = (gap.isna() | (gap > gap_seconds)).cumsum()

    # 그룹 이름: G번호_그룹 첫 사진 시각 (예: G03_250410_1444)
    first_time = df.groupby(group_no)["capture_time"].transform("min")
    df["capture_group"] = [
        f"G{n:02d}_{t:%y%m%d_%H%M}" for n, t in zip(group_no, first_time)
    ]
    return df


# ------------------------------------------------------------------
# 라벨 TXT에서 Class ID 읽기 (Class 분포 확인용)
# ------------------------------------------------------------------
def read_label_classes(label_path: Path) -> list[int] | None:
    """파일이 없으면 None, 빈 TXT(정상 김치)면 빈 리스트"""
    if not label_path.exists():
        return None
    classes = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 5:
            classes.append(int(float(parts[0])))
    return classes


# ------------------------------------------------------------------
# ③ Split 정책 적용 — capture_group 단위로만 배정
#    scene_type별로 따로 나눠야 정상 김치·객체 단독 이미지가 한쪽에 몰리지 않음
#    1) 그룹의 대표 scene_type(가장 많은 것)으로 그룹을 분류
#    2) scene_type마다 seed로 그룹 순서를 섞음
#    3) Val → Test → Bridge Holdout 순으로 목표 장수에 "가장 가까워질 때만" 그룹 추가
#    4) 남은 그룹은 Train
# ------------------------------------------------------------------
def assign_splits(
    df: pd.DataFrame,
    val_ratio: float,
    test_ratio: float,
    bridge_ratio: float,
    seed: int,
) -> pd.DataFrame:
    df = df.copy()
    rng = random.Random(seed)

    grp = df.groupby("capture_group").agg(
        size=("relative_path", "size"),
        scene=("scene_type", lambda s: Counter(s).most_common(1)[0][0]),
    )
    ratios = {"val": val_ratio, "test": test_ratio, "bridge_holdout": bridge_ratio}
    assigned: dict[str, str] = {}

    for scene in sorted(grp["scene"].unique()):
        groups = sorted(grp.index[grp["scene"] == scene])
        rng.shuffle(groups)
        scene_total = int(grp.loc[groups, "size"].sum())

        for split, ratio in ratios.items():
            target = round(scene_total * ratio)
            count = 0
            for g in groups:
                if g in assigned:
                    continue
                size = int(grp.loc[g, "size"])
                # 넣었을 때 목표에 더 가까워지면 넣는다 (큰 그룹으로 목표를 크게 넘는 것 방지)
                if abs(count + size - target) < abs(count - target):
                    assigned[g] = split
                    count += size

    for g in grp.index:
        assigned.setdefault(g, "train")

    df["split"] = df["capture_group"].map(assigned)
    return df


# ------------------------------------------------------------------
# ④ 성공 기준 검사 (가이드 예시 3의 6·7번)
# ------------------------------------------------------------------
def validate_splits(df: pd.DataFrame, expected_total: int | None) -> list[str]:
    issues: list[str] = []

    # 900장 모두 네 역할 중 하나
    bad = df[~df["split"].isin(SPLITS)]
    if len(bad):
        issues.append(f"[NO_SPLIT] 역할이 없는 이미지 {len(bad)}장")
    if expected_total is not None and len(df) != expected_total:
        issues.append(f"[TOTAL] 전체 {len(df)}장 ≠ {expected_total}장")

    # 같은 이미지가 두 역할에 있지 않은가
    if df["relative_path"].duplicated().any():
        issues.append("[DUPLICATE] 같은 이미지가 두 번 이상 배정됨")

    # 같은 촬영 그룹이 여러 역할에 섞이지 않았는가
    mixed = df.groupby("capture_group")["split"].nunique()
    if (mixed > 1).any():
        issues.append(f"[GROUP_LEAK] 여러 역할에 걸친 그룹: {mixed[mixed > 1].index.tolist()}")

    # scene_type이 한쪽에 몰리지 않았는가
    for scene in df["scene_type"].unique():
        for split in ["val", "test"]:
            if not ((df["split"] == split) & (df["scene_type"] == scene)).any():
                issues.append(f"[SCENE_MISSING] {split}에 {scene} 이미지가 없습니다")

    # Val/Test에 빠진 Class (라벨을 읽은 경우만)
    if df["classes"].notna().all():
        for split in ["val", "test"]:
            present = set()
            for cls_list in df.loc[df["split"] == split, "classes"]:
                present.update(cls_list)
            for c in range(NUM_CLASSES):
                if c not in UNUSED_CLASSES and c not in present:
                    issues.append(f"[CLASS_MISSING] {split}에 Class {c} 객체가 없습니다")
    else:
        n = df["classes"].isna().sum()
        issues.append(f"[LABEL_NOT_FOUND] 라벨 TXT {n}개를 찾지 못해 Class 분포 검사를 건너뜀")

    return issues


# ------------------------------------------------------------------
# ⑤ 분포 요약 + 저장 (가이드 예시 3의 5·10번)
# ------------------------------------------------------------------
def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS + ["TOTAL"]:
        part = df if split == "TOTAL" else df[df["split"] == split]
        row = {
            "split": split,
            "images": len(part),
            "capture_groups": part["capture_group"].nunique(),
        }
        for src, n in part["source_dataset"].value_counts().items():
            row[f"src_{src}"] = int(n)
        for osp, n in part["original_split"].value_counts().items():
            row[f"orig_{osp}"] = int(n)
        for scene, n in part["scene_type"].value_counts().items():
            row[f"scene_{scene}"] = int(n)
        if part["classes"].notna().all():
            bbox = Counter(c for cls_list in part["classes"] for c in cls_list)
            for c in range(NUM_CLASSES):
                row[f"class{c}_bbox"] = int(bbox.get(c, 0))
        rows.append(row)
    return pd.DataFrame(rows).fillna(0)


def save_outputs(df: pd.DataFrame, project_root: Path) -> None:
    manifest_dir = project_root / "manifests"
    report_dir = project_root / "reports"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    out = df.drop(columns=["classes"])
    out["capture_time"] = out["capture_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    out.to_csv(manifest_dir / "split_manifest.csv", index=False, encoding="utf-8-sig")
    for split in SPLITS:
        out[out["split"] == split].to_csv(
            manifest_dir / f"{split}.csv", index=False, encoding="utf-8-sig"
        )
    build_summary(df).to_csv(report_dir / "dataset_summary.csv", index=False, encoding="utf-8-sig")


# ------------------------------------------------------------------
# 전체 연결 (scripts/03_build_split.py에서 호출)
# ------------------------------------------------------------------
def build_split(
    manifest_path: Path,
    data_root: Path,
    project_root: Path,
    dataset_version: str,
    gap_seconds: int = 120,
    val_ratio: float = 0.20,
    test_ratio: float = 0.15,
    bridge_ratio: float = 0.10,
    seed: int = 42,
    expected_total: int | None = 900,
    save: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    df = load_manifest(manifest_path)
    df = make_capture_group(df, gap_seconds)
    df["classes"] = df["label_relative_path"].apply(lambda p: read_label_classes(data_root / p))
    df = assign_splits(df, val_ratio, test_ratio, bridge_ratio, seed)
    df["dataset_version"] = dataset_version

    issues = validate_splits(df, expected_total)
    if save:
        save_outputs(df, project_root)
    return df, issues