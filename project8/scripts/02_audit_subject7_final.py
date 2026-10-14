"""
02_audit_subject7_final.py — 2일차 Dataset Audit 실행 Script

실행 (프로젝트 루트에서):
    python scripts/02_audit_subject7_final.py

입력 : data/final/manifest_final.csv, data/final/images/, data/final/labels/
출력 : reports/audit_issue.csv
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_audit import audit_dataset, build_distribution, save_bbox_stats, save_issues

DATA_DIR = PROJECT_ROOT / "data" / "final"
MANIFEST_PATH = DATA_DIR / "manifest_final.csv"
IMAGE_DIR = DATA_DIR / "images"
LABEL_DIR = DATA_DIR / "labels"
EXPECTED_TOTAL = 900


def main():
    for path in [MANIFEST_PATH, IMAGE_DIR, LABEL_DIR]:
        if not path.exists():
            raise FileNotFoundError(f"찾을 수 없습니다: {path}")

    issue_df, image_df = audit_dataset(MANIFEST_PATH, IMAGE_DIR, LABEL_DIR)
    dist = build_distribution(image_df)

    print("=" * 55)
    print(f"Manifest 이미지 수 : {len(image_df)} (기대 {EXPECTED_TOTAL})")
    print(f"라벨 TXT 찾음      : {int(image_df['label_found'].sum())}")
    print(f"Empty Label        : {int((image_df['label_found'] & (image_df['bbox_count'] == 0)).sum())}")
    print(f"전체 BBox          : {int(image_df['bbox_count'].sum())}")
    print("=" * 55)

    titles = {
        "dataset_x_split": "Dataset × original_split",
        "scene_type": "scene_type × original_split",
        "class": "Class별 BBox 수 / 등장 이미지 수",
        "class_x_scene": "Class × scene_type (BBox 수)",
        "bbox_per_image": "이미지별 BBox 수",
        "bbox_area_by_class": "BBox 면적 — Class별 (area% = 이미지 대비 %, side640 = 640 리사이즈 후 한 변 px)",
        "bbox_area_by_scene": "BBox 면적 — scene_type별",
        "bbox_size_bucket": "BBox 크기 구간 — Class × (640 기준 한 변)",
    }
    for key, title in titles.items():
        if key not in dist:
            continue
        print(f"\n[{title}]")
        print(dist[key].to_string())

    print("\n[발견한 문제]")
    if issue_df.empty:
        print("없음")
    else:
        print(issue_df.groupby(["level", "code"]).size().to_string())

    if image_df["img_w"].isna().any():
        n = int(image_df["img_w"].isna().sum())
        print(f"\n[안내] 이미지 {n}장의 크기를 읽지 못해 정사각형으로 가정했습니다 (이미지 누락 또는 Pillow 미설치)")

    for out in [save_issues(issue_df, PROJECT_ROOT), save_bbox_stats(image_df, PROJECT_ROOT)]:
        print(f"저장: {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()