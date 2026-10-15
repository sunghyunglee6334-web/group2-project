"""
03_build_split.py — 3일차 Split Freeze 실행 Script (MVP: 그룹 단위 층화 배정)

실행 (project8 폴더에서):
    python scripts/03_build_split.py

입력 : data/final/manifest_final.csv, data/final/images, data/final/labels  (원본, 건드리지 않음)
출력 : SAVE_MANIFESTS = True →  manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
                                reports/dataset_summary.csv, reports/split_report.md
       COPY_IMAGES = True    →  data/yolo/{images,labels}/{train,val,test}, data/bridge_holdout/{images,labels}
                                configs/dataset.yaml

단계 (src/split_builder.py)
  [1단계] 누수 방지 그룹 만들기   촬영 시각 정렬 → Δt > GAP_SECONDS면 새 그룹 → 해시 병합 → 크기 확인
                                  → 같은 위치·다른 이물 쌍 체크 (1-5)
  [2단계] 그룹 속성 계산          scene_type 최빈값, 클래스 다양성(0/1-2/3-4/5-6), 희소 클래스, 객체 수, 빈 라벨 비율
                                  + Class × bbox 크기(small/medium/large) (2-4a, 2-4b)
  [3단계] 그룹 단위 층화 배정     bridge_holdout 150 → test 75 → val 75 → train 600(나머지)
                                  모든 split을 묶음째 배정 (누수 없음). Val은 기존 validation 비율이 높은 묶음을 우선
  [4단계] 검증                    그룹이 여러 split에 걸치지 않는지, split별 분포 비교
  [5단계] manifests 저장          산출물 1 (5개 CSV) 저장 후 다시 읽어 장수·겹침 확인
  [6단계] YOLO 폴더 복사 (선택)
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.split_builder import SPLITS, SplitError, build_split

# ==================================================================
# 정책 값 — docs/split_policy.md에서 확정한 값으로 여기만 고칩니다
# ==================================================================
DATASET_VERSION = "kimchi_v1"   # TODO(기준선)
GAP_SECONDS = 300               # [1-2] 5분 넘게 쉬면 새 그룹 (쉬는 동안 이물이 바뀜) — 팀 결정: 원래 기준 유지
SEED = 42                       # 기록용 (배정은 결정적 → 누가 실행해도 같은 결과)
EXPECTED_TOTAL = 900

# src/split_builder.py의 DEFAULT_POLICY 중 바꿀 값만 적습니다
POLICY = {
    "sizes": {"bridge_holdout": 150, "test": 75, "val": 75},   # [3단계] train = 나머지 600
    # ── 팀 결정 (2026-10-15): Val = T02 + T04 통째 + T17 뒤 15장 ──
    "pinned_val": ["T02"],                               # [3-2] 정상 김치(T02) + 김치·이물(T04) 묶음째
    "orig_val_block": {"enabled": True, "take": 15},            # [1-6] T17 끝 기존 validation 중 뒤 15장 (이물만)
    "use_phash": False,                                         # 배정은 그대로 두고 pHash는 06_check_phash.py로 따로 확인
    # "size_tolerance": 0,                    # 0 = 장수 정확히
    # "rare_classes": ["6"],                  # [2-3] 희소 클래스
    # "pinned_train": [],                     # [3-2] Train에 직접 고정할 group_id
    # "pinned_val": ["T02"],                  # [3-2] Val에 묶음째 고정 (기본: T02 정상 김치) · 끄려면 []
    # "orig_val_block": {"enabled": True, "take_range": [15, 30]},  # [1-5] T17 끝 기존 validation 블록을 Val로 (같은 이물 → same_bundle_split 표시)
    # "val_first": {"enabled": True},         # [3-0] 기존 validation 사진만 Val로 (묶음을 쪼갬 → 누수, 기본 끔)
    # "use_phash": True,                      # [1-3] pHash 병합 (imagehash 필요)
    # "score_weights": {"stratum": 0.5, "scene": 1.0, "class": 1.0, "background": 1.0, "size": 1.0},  # [3-4] 점수 가중치
    # "scene_pair": {"mode": "merge", "min_iou": 0.8},  # [1-5] 같은 위치·다른 이물 (merge = 묶음 합침 / flag = 표시만)
    # "size_bins": {"train_px": 640, "small": 32, "large": 96},  # [2-4a] bbox 크기 구간 (학습 해상도 기준 px)
    # "size_check": True,                     # [3-3a] Val·Test Class별 크기 쏠림(90% 초과) 금지
    # "class_min_objects": {"val": 5, "test": 5},       # [3-3] Val·Test Class별 최소 객체 수
    # "train_min_background_share": 0.5,                # [3-3] 배경 이미지 중 Train 최소 비율
    # "orig_val_preference": {"enabled": True, "weight": 2.0},  # [3-4] 기존 validation 비율 높은 묶음을 Val로 우선
}

SAVE_MANIFESTS = True   # [5단계] manifests/ 5개 CSV + reports/ 저장 (산출물 1)
COPY_IMAGES = False     # [6단계] data/yolo/, data/bridge_holdout/로 이미지·라벨 복사 (확정 후 True)

# ==================================================================
DATA_ROOT = PROJECT_ROOT / "data" / "final"
MANIFEST_PATH = DATA_ROOT / "manifest_final.csv"


def main():
    try:
        df, issues = build_split(
            manifest_path=MANIFEST_PATH, data_root=DATA_ROOT, project_root=PROJECT_ROOT,
            dataset_version=DATASET_VERSION, gap_seconds=GAP_SECONDS, seed=SEED,
            expected_total=EXPECTED_TOTAL, save=SAVE_MANIFESTS, copy_images=COPY_IMAGES,
            policy=POLICY,
        )
    except SplitError as e:
        print(f"[실패] {e}")
        sys.exit(1)

    gt, dist = df.attrs["groups"], df.attrs["distribution"]

    print("=" * 70)
    print(f"Dataset Version {DATASET_VERSION} · gap {GAP_SECONDS}s · 이미지 {len(df)}장")
    print("=" * 70)
    for line in df.attrs["log"]:
        print(" ", line)

    print("\n[2단계] 그룹 속성")
    cols = ["n_images", "scene_mode", "diversity", "has_rare", "n_objects", "empty_ratio", "ambiguous", "split"]
    print(gt[cols].to_string())

    print("\n[4단계] split별 분포")
    print(dist.set_index("split").reindex(SPLITS).T.to_string())

    sd = df.attrs.get("size_distribution")
    if sd is not None and not sd.empty:
        print("\n[4-5] Class × bbox 크기 비율(%) — all = 전체 900장")
        print(sd.pivot_table(index=["class", "split"], values=["small_pct", "medium_pct", "large_pct"])
                [["small_pct", "medium_pct", "large_pct"]].to_string())
    print(f"\n[1-5] 같은 위치·다른 이물 쌍: {len(df.attrs.get('scene_pairs', []))}개 (reports/scene_pairs.csv)")

    print("\n[4단계] 검증")
    for name, ok, detail in df.attrs["results"]:
        print(f"  {'✅' if ok else '❌'} {name}" + ("" if ok else f" — {detail}"))

    if issues:
        print("\n[확인 필요]")
        for msg in issues:
            print("  -", msg)

    print()
    if SAVE_MANIFESTS:
        print("[5단계] 저장: manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv")
        print("        기록: reports/dataset_summary.csv, reports/split_report.md")
    else:
        print("[5단계] 시험 실행 — manifests를 저장하지 않았습니다 (SAVE_MANIFESTS = True로 저장)")
    print("[6단계] 복사: data/yolo/, data/bridge_holdout/, configs/dataset.yaml" if COPY_IMAGES
          else "[6단계] 이미지 복사는 건너뜀 (COPY_IMAGES = True로 복사)")


if __name__ == "__main__":
    main()