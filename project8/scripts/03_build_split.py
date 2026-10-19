"""
03_build_split_v4.py — Split v4-B 실행 (묶음 단위 · 배정 직접 지정)

실행 (project8 폴더에서):
    python scripts/03_build_split_v4.py

입력 : data/final/manifest_final.csv, data/final/images, data/final/labels  (원본, 건드리지 않음)
출력 (기존 파일에 덮어쓰기):
       manifests/      split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
       reports/        split_report.md, dataset_summary.csv, coverage.csv, size_distribution.csv
       data/yolo/, data/bridge_holdout/, configs/dataset.yaml   (COPY_IMAGES = True)
백업 : 덮어쓰기 전에 기존 파일을 backup/split_<시각>/ 으로 옮김 (BACKUP = True)
       → 이전 Split 이미지가 새 폴더에 섞이지 않음
"""
from datetime import datetime
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.split_builder import SPLITS, SplitError, build_split

# ==================================================================
# 정책 값 — 여기만 고칩니다 (나머지는 src/split_builder.py의 DEFAULT_POLICY)
# ==================================================================
DATASET_VERSION = "kimchi_v4"
GAP_SECONDS = 300               # 5분 넘게 쉬면 새 묶음 — 팀 결정: 원래 기준 유지
EXPECTED_TOTAL = 900

POLICY = {
    # v4-B 팀 결정: 적힌 묶음만 그 split, 나머지는 모두 Train (묶음 쪼개기 없음)
    "assignment": {
        "val": ["T01", "T03", "T07"],                     # 66장
        "test": ["T08", "T14"],                           # 75장 (v1과 같음)
        "bridge_holdout": ["T09", "T11", "T16"],          # 150장 (v1과 같음)
    },
    "sizes": {"val": 66, "test": 75, "bridge_holdout": 150},   # train = 609. 장수가 다르면 실패
    "export": {                                    # 기존 경로에 덮어쓰기
        "manifest_dir": "manifests", "report_dir": "reports",
        "yolo_dir": "data/yolo", "bridge_dir": "data/bridge_holdout",
        "dataset_yaml": "configs/dataset.yaml",
    },
}

SAVE_MANIFESTS = True   # manifests + reports 저장
COPY_IMAGES = True      # data/yolo, data/bridge_holdout 로 이미지·라벨 복사
BACKUP = True           # 덮어쓰기 전에 기존 파일을 backup/split_<시각>/ 으로 옮김

DATA_ROOT = PROJECT_ROOT / "data" / "final"
MANIFEST_PATH = DATA_ROOT / "manifest_final.csv"


def backup_old_outputs() -> Path | None:
    """덮어쓸 기존 파일·폴더를 backup/split_<시각>/ 으로 옮김 (같은 상대 경로 유지)"""
    ex = POLICY["export"]
    targets = [Path(ex["manifest_dir"]) / f"{n}.csv" for n in ["split_manifest", *SPLITS]]
    targets += [Path(ex["report_dir"]) / n for n in
                ["split_report.md", "dataset_summary.csv", "coverage.csv", "size_distribution.csv", "phash_check.csv"]]
    if COPY_IMAGES:
        targets += [Path(ex["yolo_dir"]), Path(ex["bridge_dir"]), Path(ex["dataset_yaml"])]
    targets = [t for t in targets if (PROJECT_ROOT / t).exists()]
    if not targets:
        return None
    dest = PROJECT_ROOT / "backup" / f"split_{datetime.now():%Y%m%d_%H%M%S}"
    for t in targets:
        (dest / t).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(PROJECT_ROOT / t), str(dest / t))
    return dest


def run(save, copy):
    return build_split(
        manifest_path=MANIFEST_PATH, data_root=DATA_ROOT, project_root=PROJECT_ROOT,
        dataset_version=DATASET_VERSION, gap_seconds=GAP_SECONDS,
        expected_total=EXPECTED_TOTAL, save=save, copy_images=copy, policy=POLICY,
    )


def main():
    backup = None
    try:
        if BACKUP and (SAVE_MANIFESTS or COPY_IMAGES):
            run(False, False)                        # 먼저 검사만 → 실패하면 기존 파일은 그대로
            backup = backup_old_outputs()
        df, issues = run(SAVE_MANIFESTS, COPY_IMAGES)
    except SplitError as e:
        print(f"[실패] {e}")
        if backup:
            print(f"  기존 파일 백업: {backup}")
        sys.exit(1)

    gt, dist, cov = df.attrs["groups"], df.attrs["distribution"], df.attrs["coverage"]
    print("=" * 70)
    print(f"Dataset Version {DATASET_VERSION} · gap {GAP_SECONDS}s · 이미지 {len(df)}장")
    print("=" * 70)
    for line in df.attrs["log"]:
        print(" ", line)

    print("\n[2단계] 묶음 속성")
    print(gt[["n_images", "scene_mode", "class_union", "n_objects", "empty_ratio", "ambiguous", "split"]].to_string())

    print("\n[4단계] split별 분포")
    print(dist.set_index("split").reindex(SPLITS).T.to_string())

    print("\n[4-4] 평가할 수 있는가 (Val·Test에 있는지)")
    print(cov.to_string(index=False))

    print("\n[4단계] 검증")
    for name, ok, detail in df.attrs["results"]:
        print(f"  {'✅' if ok else '❌'} {name}" + ("" if ok else f" — {detail}"))

    if issues:
        print("\n[확인 필요]")
        for msg in issues:
            print("  -", msg)

    ex = POLICY["export"]
    print()
    print(f"[5단계] 저장: {ex['manifest_dir']}/ · 기록: {ex['report_dir']}/" if SAVE_MANIFESTS
          else "[5단계] 시험 실행 — 저장하지 않음 (SAVE_MANIFESTS = True로 저장)")
    print(f"[6단계] 복사: {ex['yolo_dir']}/, {ex['bridge_dir']}/, {ex['dataset_yaml']}" if COPY_IMAGES
          else "[6단계] 이미지 복사는 건너뜀 (COPY_IMAGES = True로 복사)")
    if backup:
        print(f"[백업] 기존 파일 → {backup.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
