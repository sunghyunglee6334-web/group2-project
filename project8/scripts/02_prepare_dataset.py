"""받은 data -> 학습용 구조 정리

src/project_config.py 의 SOURCE_SPLITS 를 읽어
  train · val · test     -> data/yolo/images|labels/<split>
  bridge_holdout         -> data/bridge_holdout/images|labels
로 복사하고 configs/dataset.yaml (Bridge 제외) · manifests · reports 를 만든다.
문제가 하나라도 있으면 복사하지 않고 reporte.s/audit_issucsv 만 남긴다.

    python scripts/02_prepare_dataset.py --dry-run   # 검사 · 개수만
    python scripts/02_prepare_dataset.py
"""
import argparse
import csv
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_check import list_images, read_label  # noqa: E402
from src.project_config import (  # noqa: E402
    BRIDGE_DIR,
    CLASS_NAMES,
    DATASET_VERSION,
    DATASET_YAML,
    MANIFEST_DIR,
    RAW_DATA_DIR,
    REPORT_DIR,
    SOURCE_MANIFEST,
    SOURCE_SPLITS,
    YOLO_DIR,
)

SPLITS = ["train", "val", "test", "bridge_holdout"]
MANIFEST_COLUMNS = [
    "image_path", "label_path", "source_dataset", "original_split",
    "scene_type", "capture_group", "split", "dataset_version",
]
JOIN_COLUMNS = ["source_dataset", "original_split", "scene_type", "capture_group"]


def source_dirs(split):
    cfg = SOURCE_SPLITS[split]
    return RAW_DATA_DIR / cfg["images"], RAW_DATA_DIR / cfg["labels"]


def target_dirs(split):
    if split == "bridge_holdout":
        return BRIDGE_DIR / "images", BRIDGE_DIR / "labels"
    return YOLO_DIR / "images" / split, YOLO_DIR / "labels" / split


def load_source_manifest():
    """SOURCE_MANIFEST 에서 image_name -> {source_dataset, scene_type, ...}"""
    if not SOURCE_MANIFEST:
        return {}
    rows = {}
    with open(SOURCE_MANIFEST, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            name = r.get("image_name") or Path(r.get("relative_path", "")).name
            if name:
                rows[name] = {k: r.get(k, "") for k in JOIN_COLUMNS}
    print(f"SOURCE_MANIFEST {SOURCE_MANIFEST} : {len(rows)}행")
    return rows


def scan():
    """모든 split 을 검사 -> (split 별 짝 목록, 문제 목록, 요약)"""
    pairs, issues, summary = {}, [], []
    seen = {}  # 이미지 이름 -> 처음 나온 split (split 간 중복 = 누수)
    for split in SPLITS:
        img_dir, lbl_dir = source_dirs(split)
        missing_dir = [str(d) for d in (img_dir, lbl_dir) if not d.is_dir()]
        if missing_dir:
            for d in missing_dir:
                issues.append((split, d, "missing_dir", "폴더 없음 (SOURCE_SPLITS 확인)"))
            pairs[split] = []
            summary.append({"role": split, "image_count": 0, "empty_label_count": 0, "bbox_count": 0})
            continue

        images = list_images(img_dir)
        image_stems = {p.stem for p in images}
        for lbl in sorted(lbl_dir.glob("*.txt")):
            if lbl.stem not in image_stems:
                issues.append((split, lbl.name, "orphan_label", "짝 이미지 없음"))

        split_pairs, class_count, empty = [], Counter(), 0
        for img in images:
            if img.name in seen:
                issues.append((split, img.name, "duplicate_across_splits", f"{seen[img.name]} 에도 있음"))
            seen.setdefault(img.name, split)

            lbl = lbl_dir / f"{img.stem}.txt"
            if not lbl.exists():
                issues.append((split, img.name, "missing_label", "짝 TXT 없음"))
                continue
            classes, problems = read_label(lbl)
            for kind, detail in problems:
                issues.append((split, lbl.name, kind, detail))
            empty += not classes
            class_count.update(classes)
            split_pairs.append((img, lbl))

        pairs[split] = split_pairs
        row = {"role": split, "image_count": len(split_pairs), "empty_label_count": empty,
               "bbox_count": sum(class_count.values())}
        row.update({f"c{c}_{n}": class_count[c] for c, n in CLASS_NAMES.items()})
        summary.append(row)

    total = {"role": "total"}
    for key in summary[0]:
        if key != "role":
            total[key] = sum(r.get(key, 0) for r in summary)
    summary.append(total)
    return pairs, issues, summary


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def copy_and_manifest(pairs, meta):
    for d in (YOLO_DIR, BRIDGE_DIR):
        if d.exists():
            shutil.rmtree(d)  # 02 가 만드는 파생 폴더라 매번 새로 만든다

    all_rows = []
    for split in SPLITS:
        out_img, out_lbl = target_dirs(split)
        out_img.mkdir(parents=True)
        out_lbl.mkdir(parents=True)
        rows = []
        for img, lbl in pairs[split]:
            shutil.copy2(img, out_img / img.name)
            shutil.copy2(lbl, out_lbl / lbl.name)
            row = {
                "image_path": (out_img / img.name).relative_to(PROJECT_ROOT).as_posix(),
                "label_path": (out_lbl / lbl.name).relative_to(PROJECT_ROOT).as_posix(),
                "split": split,
                "dataset_version": DATASET_VERSION,
            }
            row.update(meta.get(img.name, {}))
            rows.append(row)
        write_csv(MANIFEST_DIR / f"{split}.csv", rows, MANIFEST_COLUMNS)
        all_rows += rows
        print(f"[{split}] {len(rows)}쌍 -> {out_img.relative_to(PROJECT_ROOT)}")
    write_csv(MANIFEST_DIR / "split_manifest.csv", all_rows, MANIFEST_COLUMNS)

    unmatched = sum(1 for r in all_rows if meta and not r.get("scene_type"))
    if meta and unmatched:
        print(f"주의: SOURCE_MANIFEST 와 매칭 안 된 이미지 {unmatched}장 (scene_type 빈칸)")


def write_dataset_yaml():
    data = {
        "path": str(YOLO_DIR),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": CLASS_NAMES,
    }
    DATASET_YAML.parent.mkdir(parents=True, exist_ok=True)
    text = f"# {DATASET_VERSION} · 02_prepare_dataset.py 가 생성 · Bridge Holdout 미포함\n"
    DATASET_YAML.write_text(text + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"YAML -> {DATASET_YAML.relative_to(PROJECT_ROOT)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="검사 · 개수만 보고 (복사 안 함)")
    args = parser.parse_args()

    print(f"RAW_DATA_DIR: {RAW_DATA_DIR}")
    pairs, issues, summary = scan()

    write_csv(REPORT_DIR / "audit_issue.csv",
              [dict(zip(["split", "file", "issue", "detail"], i)) for i in issues],
              ["split", "file", "issue", "detail"])
    write_csv(REPORT_DIR / "dataset_summary.csv", summary, list(summary[0].keys()))

    print(f"{'role':<16}{'images':>8}{'empty':>8}{'bbox':>8}")
    for r in summary:
        print(f"{r['role']:<16}{r['image_count']:>8}{r['empty_label_count']:>8}{r['bbox_count']:>8}")

    if issues:
        print(f"\n문제 {len(issues)}건 -> reports/audit_issue.csv (복사하지 않음)")
        for kind, n in Counter(i[2] for i in issues).most_common():
            print(f"  {kind}: {n}")
        raise SystemExit(1)
    print("\n문제 없음")
    if args.dry_run:
        print("--dry-run: 복사하지 않음")
        return

    copy_and_manifest(pairs, load_source_manifest())
    write_dataset_yaml()
    print("완료")


if __name__ == "__main__":
    main()
