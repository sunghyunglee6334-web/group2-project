"""
03_build_split.py — 3일차 Split Freeze 실행 Script

실행 (프로젝트 루트에서):
    python scripts/03_build_split.py

입력 : manifests/manifest_final.csv   (교과 7 Master Manifest)
       data/subject7_final/            (교과 7 FINAL 이미지·라벨, Manifest 경로의 기준 폴더)
출력 : manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
       reports/dataset_summary.csv
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.split_builder import SPLITS, build_split

# ==================================================================
# 정책 값 — docs/split_policy.md에서 확정한 값으로 여기만 고칩니다
# (현재 값은 모두 임시값, TBD)
# ==================================================================
DATASET_VERSION = "kimchi_v1"

GAP_SECONDS = 120      # 앞 사진과 몇 초 넘게 벌어지면 다른 촬영 묶음으로 볼지
VAL_RATIO = 0.20       # 전체 중 Validation 비율
TEST_RATIO = 0.15      # 전체 중 Frozen Test 비율
BRIDGE_RATIO = 0.10    # 전체 중 Bridge Holdout 비율 (나머지는 Train)
SEED = 42              # 같은 seed → 누가 실행해도 같은 결과

EXPECTED_TOTAL = 900   # 교과 7 FINAL 장수

# 실제로 파일을 저장할지 (정책 확정 전 시험 실행은 False 권장)
SAVE = False

# ==================================================================
# 경로
# ==================================================================
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "manifest_final.csv"
DATA_ROOT = PROJECT_ROOT / "data" / "subject7_final"


def main():
    if not DATA_ROOT.exists():
        print(f"[안내] 데이터 폴더가 없습니다: {DATA_ROOT}  → Class 분포 검사는 건너뜁니다")

    df, issues = build_split(
        manifest_path=MANIFEST_PATH,
        data_root=DATA_ROOT,
        project_root=PROJECT_ROOT,
        dataset_version=DATASET_VERSION,
        gap_seconds=GAP_SECONDS,
        val_ratio=VAL_RATIO,
        test_ratio=TEST_RATIO,
        bridge_ratio=BRIDGE_RATIO,
        seed=SEED,
        expected_total=EXPECTED_TOTAL,
        save=SAVE,
    )

    # ---- 실행조건 ----
    print("=" * 50)
    print(f"Dataset Version : {DATASET_VERSION}")
    print(f"gap / seed      : {GAP_SECONDS}s / {SEED}")
    print(f"비율 (val/test/bridge): {VAL_RATIO} / {TEST_RATIO} / {BRIDGE_RATIO}")
    print(f"촬영 묶음 수    : {df['capture_group'].nunique()}")
    print("=" * 50)

    # ---- 역할별 수량 ----
    counts = df["split"].value_counts().reindex(SPLITS, fill_value=0)
    for split, n in counts.items():
        groups = df.loc[df["split"] == split, "capture_group"].nunique()
        print(f"{split:<15}{n:>5}장  ({n / len(df):5.1%}, 묶음 {groups}개)")
    print(f"{'합계':<14}{len(df):>5}장")

    # ---- scene_type 분포 ----
    print("\n[scene_type 분포]")
    print(df.pivot_table(index="split", columns="scene_type", values="relative_path",
                         aggfunc="count", fill_value=0).reindex(SPLITS))

    # ---- 검증 ----
    print()
    if issues:
        print("[확인 필요]")
        for msg in issues:
            print(" -", msg)
    else:
        print("모든 검증 통과")

    print()
    print("저장 완료: manifests/, reports/dataset_summary.csv" if SAVE
          else "시험 실행 — 파일은 저장하지 않았습니다 (SAVE = True로 바꾸면 저장)")


if __name__ == "__main__":
    main()