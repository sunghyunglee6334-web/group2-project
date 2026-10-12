"""팀원들의 WORK 폴더를 하나로 합친다 (하루 끝날 때 PM/Data 담당이 실행).

각 팀원은 자기 PC 의 data/work 폴더(= manifest.csv + labels/)를 공유폴더에 복사해 둔다.
같은 이미지는 manifest 의 updated_at 이 가장 최신인 사람의 결과를 사용한다.
같은 이미지를 두 사람이 수정했으면 conflicts 보고서에 남긴다.

    python scripts/04_merge.py --inputs D:/share/work_A D:/share/work_B ... --out D:/share/work_merged
그 다음 work_merged 를 모두가 자기 data/work 로 받아서 이어서 작업한다.
"""
import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import REPORT_DIR  # noqa: E402
from src.manifest import Manifest, merge_manifests  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="팀원 WORK 폴더들")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ins = [Path(p).resolve() for p in a.inputs]
    out = Path(a.out).resolve()
    if out in ins:
        raise SystemExit("--out 은 입력 폴더와 달라야 합니다.")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} 가 비어 있지 않습니다. 새 폴더를 지정하세요.")
    for p in ins:
        if not (p / "manifest.csv").exists():
            raise SystemExit(f"manifest.csv 없음: {p}")
    rows, origin = merge_manifests([p / "manifest.csv" for p in ins])

    # 확인 필요 목록
    #  - 담당자/검수자가 아닌 사람이 수정한 경우 (같은 이미지 동시 작업 의심)
    #  - REVIEWED 이후 담당자가 다시 수정한 경우 (재검수 필요)
    edits: dict[str, list[dict]] = {}
    for p in ins:
        for key, r in Manifest(p / "manifest.csv").rows.items():
            if r["updated_by"] not in ("", "builder", "assign"):
                edits.setdefault(key, []).append(dict(r, _folder=p.name))
    conflicts: dict[str, str] = {}
    for key, lst in edits.items():
        win = rows[key]
        editors = {r["updated_by"] for r in lst}
        allowed = {win["assignee"], win["reviewer"]}
        if not editors <= allowed:
            conflicts[key] = "담당/검수자 외 수정: " + ", ".join(sorted(editors - allowed))
        elif win["status"] != "REVIEWED" and any(r["status"] == "REVIEWED" for r in lst):
            conflicts[key] = "REVIEWED 이후 다시 수정됨 -> 재검수 필요"

    copied = 0
    for key, r in rows.items():
        src = origin[key].parent / r["label_relative_path"]
        if not src.exists():   # 예전 버전 폴더(WORK/labels/...)로 제출된 경우
            src = origin[key].parent / "labels" / r["label_relative_path"]
        if src.exists():
            dst = out / r["label_relative_path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    snap = ins[0] / "raw_checksums.csv"
    if snap.exists():
        shutil.copy2(snap, out / "raw_checksums.csv")
    m = Manifest(out / "manifest.csv")
    m.rows = rows
    m.save()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rep = REPORT_DIR / "merge_conflicts.csv"
    with open(rep, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["relative_path", "reason"])
        for k, v in sorted(conflicts.items()):
            w.writerow([k, v])
    print(f"병합 완료: {out}  (manifest {len(rows)}행, 라벨 {copied}개)")
    print(f"동시 수정 의심 {len(conflicts)}건 -> {rep}" + ("  (확인 필요!)" if conflicts else ""))
    print("상태:", Manifest(out / "manifest.csv").count_by("status"))


if __name__ == "__main__":
    main()
