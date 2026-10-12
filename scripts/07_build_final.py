"""FINAL 생성 + Freeze.

조건을 하나라도 어기면 만들지 않는다:
  - PENDING / WORKING / REVIEW / EDITED(교차검수 안 됨) 0
  - WORK 기준 CRITICAL Validation 0
  - (raw_checksums.csv 가 있으면) RAW 가 처음과 동일
FINAL 은 images/ 와 labels/ 두 폴더에 이미지 + 최종 TXT 를 같은 이름으로 복사한다.
출처 Dataset 과 split 정보는 manifest_final.csv 와 final_file_map.csv 에 남는다.
FINAL 은 직접 수정하지 않는다.

    python scripts/07_build_final.py
"""
import argparse
import csv
import json
import shutil
import subprocess
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import FINAL_READY_STATUSES, Paths  # noqa: E402
from src.yolo.dataset import scan_images  # noqa: E402
from src.yolo.final_layout import final_image_path, final_label_path, final_stems  # noqa: E402
from src.manifest import Manifest, now_str  # noqa: E402
from src.validation.validator import critical_count, validate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw"); ap.add_argument("--work"); ap.add_argument("--final")
    a = ap.parse_args()
    paths = Paths(a.raw, a.work, a.final)
    recs = scan_images(paths.raw)
    m = Manifest(paths.manifest)
    problems = []
    not_ready = [r for r in m.rows.values() if r["status"] not in FINAL_READY_STATUSES | {"FINAL"}]
    if not_ready:
        problems.append(f"FINAL 불가 상태 {len(not_ready)}장 (예: {not_ready[0]['relative_path']} = {not_ready[0]['status']})")
    missing = [r.rel_image for r in recs if r.rel_image not in m.rows]
    if missing:
        problems.append(f"Manifest 에 없는 이미지 {len(missing)}장")
    issues = validate(paths, use_work=True, records=recs)
    if critical_count(issues):
        problems.append(f"CRITICAL Validation {critical_count(issues)}건 (02_validate.py 로 확인)")
    snap = paths.work / "raw_checksums.csv"
    if not snap.exists():
        print("[주의] RAW 스냅샷이 없어 RAW 보존 확인을 건너뜁니다 (00_raw_snapshot.py).")
    else:
        rc = subprocess.call([sys.executable, str(ROOT / "scripts" / "00_raw_snapshot.py"), "--verify",
                              "--raw", str(paths.raw), "--work", str(paths.work)], stdout=subprocess.DEVNULL)
        if rc != 0:
            problems.append("RAW 가 처음 스냅샷과 다릅니다 (00_raw_snapshot.py --verify)")
    if problems:
        print("[FINAL 생성 중단]")
        for p in problems:
            print(" -", p)
        return 1

    if paths.final.exists() and any(paths.final.iterdir()):
        backup = paths.final.with_name(paths.final.name + f"_old_{datetime.now():%Y%m%d_%H%M%S}")
        paths.final.rename(backup)
        print(f"기존 FINAL 은 {backup.name} 으로 보관했습니다.")
    stems = final_stems(recs)
    (paths.final / "images").mkdir(parents=True, exist_ok=True)
    (paths.final / "labels").mkdir(parents=True, exist_ok=True)
    file_map = []
    for rec in recs:
        dst_img = final_image_path(paths.final, rec, stems[rec.rel_image])
        dst_lbl = final_label_path(paths.final, stems[rec.rel_image])
        shutil.copy2(rec.raw_image(paths), dst_img)
        shutil.copy2(rec.effective_label(paths), dst_lbl)
        file_map.append({"relative_path": rec.rel_image, "source_dataset": rec.source_dataset,
                         "original_split": rec.original_split,
                         "final_image": f"images/{dst_img.name}", "final_label": f"labels/{dst_lbl.name}"})
    with open(paths.final / "final_file_map.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(file_map[0]))
        w.writeheader()
        w.writerows(file_map)
    fm = Manifest(paths.final / "manifest_final.csv")
    fm.rows = {k: dict(v) for k, v in m.rows.items()}
    for k in fm.rows:
        fm.rows[k]["status"] = "FINAL"
    fm.save()
    for k in m.rows:     # WORK manifest 에도 FINAL 기록
        m.rows[k]["status"] = "FINAL"
        m.rows[k]["updated_at"] = now_str()
    m.save()
    info = dict(created=now_str(), images=len(recs), labels=len(recs),
                note="FINAL 은 직접 수정하지 않는다. 문제 발견 시 WORK 수정 -> Validation -> Review -> FINAL 재생성")
    (paths.final / "FINAL_INFO.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] FINAL 생성 완료: {paths.final}  ({len(recs)}장)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
