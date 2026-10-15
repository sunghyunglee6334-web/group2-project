"""
dataset_audit.py
학습 전에 교과 7 FINAL 데이터가 정상인지 검사한다 (2일차 Dataset Audit).

입력 : data/final/manifest_final.csv + data/final/images/, data/final/labels/
       (이미지·라벨은 한 폴더에 모여 있고, 파일 이름으로 찾는다)
출력 : reports/audit_issue.csv  (발견한 문제 목록)
       reports/bbox_stats.csv   (BBox 1개 = 1행, 크기·면적)
       분포 표 (Dataset / original_split / scene_type / Class별 BBox / 이미지별 BBox / BBox 면적)

처리 순서
  ① validate_yolo_row()   TXT 한 줄 검사
  ② audit_label_file()    TXT 파일 하나 검사
  ③ audit_dataset()       Manifest 900행 전체 검사 (Pair·형식·Empty·Manifest 대조)
  ④ find_orphans()        Manifest에 없는 파일이 폴더에 있는지
  ⑤ build_distribution()  분포 집계
  ⑥ build_bbox_table()    BBox 면적 정리 (작은 객체가 얼마나 있는지)
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

NUM_CLASSES = 7
CLASS_NAMES = {
    0: "나뭇잎·종이류",
    1: "플라스틱·돌·금속",
    2: "나뭇가지류",
    3: "벌레류",
    4: "고무장갑(미사용)",
    5: "병해·갈변",
    6: "파·고추",
}
NEGATIVE_SCENE = "normal_kimchi"   # 빈 TXT가 정상인 장면
IGNORE_TXT = {"classes.txt"}       # 라벨이 아닌 TXT

# 확인된 예외 — 빈 TXT가 정답인 것으로 팀이 확인한 이미지 (split_policy.md 4-2)
# 김치 없이 고무장갑만 있는 사진: 기준서상 고무장갑 단독 = 배경 → 박스 삭제, 빈 TXT가 맞음
# 장면 유형(object_only)과 박스는 바꾸지 않는다. 여기에 없는 빈 TXT는 계속 WARN으로 잡힌다.
KNOWN_EMPTY_EXCEPTIONS = {
    "250513_021424892102.jpg": "glove_only_background",
    "250410_160155606350.jpg": "glove_only_background",
}

# BBox 크기 구간 — 학습 입력(imgsz=640)으로 줄였을 때 객체 한 변이 몇 px인지 기준
IMGSZ = 640
SIZE_BINS = [0, 8, 16, 32, 64, float("inf")]
SIZE_LABELS = ["<8px", "8-16px", "16-32px", "32-64px", "≥64px"]

ISSUE_COLUMNS = ["level", "code", "image_name", "relative_path", "line_no", "detail"]


# ------------------------------------------------------------------
# ① TXT 한 줄 검사 (가이드 15.1 예시)
# ------------------------------------------------------------------
def validate_yolo_row(row: str) -> list[str]:
    issues = []
    parts = row.strip().split()

    if len(parts) != 5:
        return ["COLUMN_COUNT"]

    try:
        cls = int(parts[0])
        x, y, w, h = map(float, parts[1:])
    except ValueError:
        return ["PARSE_ERROR"]

    if cls < 0 or cls > 6:
        issues.append("CLASS_RANGE")
    if cls == 4:
        issues.append("CLASS4_REVIEW")
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        issues.append("CENTER_RANGE")
    if not (0.0 < w <= 1.0 and 0.0 < h <= 1.0):
        issues.append("SIZE_RANGE")

    return issues


# ------------------------------------------------------------------
# ② TXT 파일 하나 검사
# ------------------------------------------------------------------
def audit_label_file(label_path: Path) -> dict:
    """
    반환 예:
    {"exists": True, "empty": False, "classes": [2, 0], "bbox_count": 2,
     "row_issues": [(3, ["SIZE_RANGE"])]}   ← (줄 번호, 문제 코드)
    """
    result = {"exists": label_path.exists(), "empty": False,
              "classes": [], "boxes": [], "bbox_count": 0, "row_issues": []}
    if not result["exists"]:
        return result

    lines = [ln for ln in label_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        result["empty"] = True
        return result

    for no, line in enumerate(lines, start=1):
        codes = validate_yolo_row(line)
        if codes:
            result["row_issues"].append((no, codes))
        if not {"COLUMN_COUNT", "PARSE_ERROR"} & set(codes):
            parts = line.split()
            cls = int(parts[0])
            result["classes"].append(cls)
            result["boxes"].append((cls, float(parts[3]), float(parts[4])))  # (class, w, h)

    result["bbox_count"] = len(result["classes"])
    return result


def read_image_size(image_path: Path) -> tuple[int | None, int | None]:
    """이미지 전체를 읽지 않고 헤더에서 (너비, 높이)만 읽는다. 실패하면 (None, None)"""
    try:
        from PIL import Image
        with Image.open(image_path) as im:
            return im.size
    except Exception:
        return None, None


# ------------------------------------------------------------------
# ③ Manifest 전체 검사
# ------------------------------------------------------------------
def audit_dataset(
    manifest_path: Path, image_dir: Path, label_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(issue_df, image_df) 반환. image_df는 이미지 1장 = 1행 (분포 집계용)"""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest를 찾을 수 없습니다: {manifest_path}")

    manifest = pd.read_csv(manifest_path)
    issues: list[dict] = []
    images: list[dict] = []

    def add(level, code, row=None, line_no="", detail=""):
        issues.append({
            "level": level, "code": code,
            "image_name": "" if row is None else row["image_name"],
            "relative_path": "" if row is None else row["relative_path"],
            "line_no": line_no, "detail": detail,
        })

    # Manifest 자체 중복
    for col in ["relative_path", "image_name"]:
        for name in manifest.loc[manifest[col].duplicated(), col]:
            add("ERROR", f"DUPLICATE_{col.upper()}", detail=name)

    for _, row in manifest.iterrows():
        # 이미지·라벨은 폴더 하나에 모여 있으므로 파일 이름으로 찾는다
        image_path = image_dir / row["image_name"]
        label_path = label_dir / row["label_name"]

        # Pair 확인
        image_ok = image_path.exists()
        img_w, img_h = read_image_size(image_path) if image_ok else (None, None)
        if not image_ok:
            add("ERROR", "IMAGE_MISSING", row, detail=f"images/{row['image_name']}")

        label = audit_label_file(label_path)
        if not label["exists"]:
            add("ERROR", "LABEL_MISSING", row, detail=f"labels/{row['label_name']}")

        # 이름 짝 확인 (abc.jpg ↔ abc.txt)
        if Path(row["image_name"]).stem != Path(row["label_name"]).stem:
            add("ERROR", "PAIR_NAME_MISMATCH", row, detail=row["label_name"])

        # 줄 단위 문제
        for line_no, codes in label["row_issues"]:
            for code in codes:
                level = "WARN" if code == "CLASS4_REVIEW" else "ERROR"
                add(level, code, row, line_no=line_no)

        # Empty Label — 바로 오류로 단정하지 않고 scene_type과 대조
        if label["exists"]:
            if label["empty"] and row["image_name"] in KNOWN_EMPTY_EXCEPTIONS:
                add("INFO", "EMPTY_GLOVE_ONLY", row,
                    detail=f"확인된 예외({KNOWN_EMPTY_EXCEPTIONS[row['image_name']]}) — "
                           "김치 없이 고무장갑만, 빈 TXT 정상")
            elif label["empty"] and row["scene_type"] != NEGATIVE_SCENE:
                add("WARN", "EMPTY_NOT_NORMAL", row,
                    detail=f"scene_type={row['scene_type']}인데 BBox 0개")
            elif label["empty"]:
                add("INFO", "EMPTY_NEGATIVE", row, detail="정상 김치 Negative Sample")
            elif row["scene_type"] == NEGATIVE_SCENE:
                add("WARN", "NORMAL_HAS_BBOX", row,
                    detail=f"normal_kimchi인데 BBox {label['bbox_count']}개")

            # 교과 7 Manifest 기록과 실제 BBox 수 대조
            if "final_bbox_count" in manifest.columns and pd.notna(row["final_bbox_count"]):
                if int(row["final_bbox_count"]) != label["bbox_count"]:
                    add("WARN", "BBOX_COUNT_MISMATCH", row,
                        detail=f"Manifest {int(row['final_bbox_count'])} / 실제 {label['bbox_count']}")

        images.append({
            "image_name": row["image_name"],
            "source_dataset": row["source_dataset"],
            "original_split": row["original_split"],
            "scene_type": row["scene_type"],
            "label_found": label["exists"],
            "bbox_count": label["bbox_count"],
            "classes": label["classes"],
            "boxes": label["boxes"],
            "img_w": img_w,
            "img_h": img_h,
        })

    # 폴더에는 있는데 Manifest에 없는 파일
    for kind, path in find_orphans(manifest, image_dir, label_dir):
        add("WARN", f"ORPHAN_{kind}", detail=f"{path.parent.name}/{path.name}")

    issue_df = pd.DataFrame(issues, columns=ISSUE_COLUMNS)
    image_df = pd.DataFrame(images)
    return issue_df, image_df


# ------------------------------------------------------------------
# ④ Manifest에 없는 파일 찾기
# ------------------------------------------------------------------
def find_orphans(
    manifest: pd.DataFrame, image_dir: Path, label_dir: Path
) -> list[tuple[str, Path]]:
    listed_images = set(manifest["image_name"])
    listed_labels = set(manifest["label_name"])
    orphans = []
    if image_dir.exists():
        for p in sorted(image_dir.glob("*.jpg")):
            if p.name not in listed_images:
                orphans.append(("IMAGE", p))
    if label_dir.exists():
        for p in sorted(label_dir.glob("*.txt")):
            if p.name not in IGNORE_TXT and p.name not in listed_labels:
                orphans.append(("LABEL", p))
    return orphans


# ------------------------------------------------------------------
# ⑤ 분포 집계 (가이드 15.1·15.2)
# ------------------------------------------------------------------
def build_distribution(image_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    found = image_df[image_df["label_found"]]
    dist = {}

    dist["dataset_x_split"] = pd.crosstab(
        image_df["source_dataset"], image_df["original_split"], margins=True, margins_name="합계")
    dist["scene_type"] = pd.crosstab(
        image_df["scene_type"], image_df["original_split"], margins=True, margins_name="합계")

    # Class별 BBox 수 + 그 Class가 나온 이미지 수
    rows = []
    for c in range(NUM_CLASSES):
        has = found["classes"].apply(lambda cl: c in cl)
        rows.append({
            "class_id": c,
            "name": CLASS_NAMES[c],
            "bbox": int(found["classes"].apply(lambda cl: cl.count(c)).sum()),
            "images": int(has.sum()),
        })
    dist["class"] = pd.DataFrame(rows)

    # Class × scene_type (BBox 수) — 특정 Class가 한 장면에만 몰렸는지
    exploded = found[["scene_type", "classes"]].explode("classes").dropna().reset_index(drop=True)
    dist["class_x_scene"] = pd.crosstab(exploded["classes"].astype(int), exploded["scene_type"])

    # 이미지별 BBox 수 분포
    dist["bbox_per_image"] = found["bbox_count"].value_counts().sort_index().to_frame("images")

    # BBox 면적 (⑥)
    bbox = build_bbox_table(image_df)
    if not bbox.empty:
        dist["bbox_area_by_class"] = summarize_bbox_area(bbox, "class_id")
        dist["bbox_area_by_scene"] = summarize_bbox_area(bbox, "scene_type")
        dist["bbox_size_bucket"] = pd.crosstab(
            bbox["class_id"], bbox["size_bucket"], margins=True, margins_name="합계"
        ).reindex(columns=SIZE_LABELS + ["합계"], fill_value=0)

    return dist


# ------------------------------------------------------------------
# ⑥ BBox 면적 정리
#    area_ratio : BBox 면적 / 이미지 면적 (YOLO w × h, 이미지 크기와 무관)
#    area_px    : 원본 이미지 기준 픽셀 면적 (이미지 크기를 읽은 경우)
#    side_640   : imgsz=640으로 줄였을 때 BBox 한 변 길이(√면적, px)
#                 → 작은 객체를 모델이 놓칠 위험을 가늠하는 값
# ------------------------------------------------------------------
def build_bbox_table(image_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, img in image_df.iterrows():
        W, H = img["img_w"], img["img_h"]
        size_known = pd.notna(W) and pd.notna(H)
        # 긴 변을 640으로 맞추는 YOLO 리사이즈 비율 (크기를 모르면 정사각형으로 가정)
        scale = IMGSZ / max(W, H) if size_known else None
        for cls, w, h in img["boxes"]:
            w_px = w * W if size_known else None
            h_px = h * H if size_known else None
            if size_known:
                side_640 = ((w_px * scale) * (h_px * scale)) ** 0.5
            else:
                side_640 = ((w * IMGSZ) * (h * IMGSZ)) ** 0.5
            rows.append({
                "image_name": img["image_name"],
                "source_dataset": img["source_dataset"],
                "original_split": img["original_split"],
                "scene_type": img["scene_type"],
                "class_id": cls,
                "class_name": CLASS_NAMES.get(cls, "?"),
                "w": w,
                "h": h,
                "area_ratio": w * h,
                "img_w": W,
                "img_h": H,
                "w_px": None if w_px is None else round(w_px, 1),
                "h_px": None if h_px is None else round(h_px, 1),
                "area_px": None if w_px is None else round(w_px * h_px),
                "side_640": round(side_640, 1),
            })
    bbox = pd.DataFrame(rows)
    if not bbox.empty:
        bbox["size_bucket"] = pd.cut(bbox["side_640"], bins=SIZE_BINS,
                                     labels=SIZE_LABELS, right=False).astype(str)
    return bbox


def summarize_bbox_area(bbox: pd.DataFrame, by: str) -> pd.DataFrame:
    """그룹별 면적 비율(%)과 640 기준 한 변(px) 요약"""
    g = bbox.groupby(by)
    out = pd.DataFrame({
        "bbox": g.size(),
        "area%_min": g["area_ratio"].min() * 100,
        "area%_median": g["area_ratio"].median() * 100,
        "area%_mean": g["area_ratio"].mean() * 100,
        "area%_max": g["area_ratio"].max() * 100,
        "side640_median": g["side_640"].median(),
        "small(<16px)": g["side_640"].apply(lambda s: int((s < 16).sum())),
    })
    out["small%"] = out["small(<16px)"] / out["bbox"] * 100
    return out.round(3)


def save_bbox_stats(image_df: pd.DataFrame, project_root: Path) -> Path:
    out = project_root / "reports" / "bbox_stats.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    build_bbox_table(image_df).to_csv(out, index=False, encoding="utf-8-sig")
    return out


def save_issues(issue_df: pd.DataFrame, project_root: Path) -> Path:
    out = project_root / "reports" / "audit_issue.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    issue_df.to_csv(out, index=False, encoding="utf-8-sig")
    return out