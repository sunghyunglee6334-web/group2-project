"""900장 작업 배분 + Reviewer 지정 + Pilot 선정.

- Dataset/split 이 고르게 섞이도록 그룹별로 돌아가며 배분한다.
- Reviewer 는 '다음 사람' (A->B, B->C, ..., F->A) : 자기 작업은 자기가 검수하지 않는다.
- 이미 assignee 가 있는 행은 바꾸지 않는다 (--force 로 재배분).

    python scripts/03_assign.py --workers 김PM 이GUI 박좌표 최저장 정QA 한문서 --pilot 30
"""
import argparse
import random
from collections import defaultdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import Paths  # noqa: E402
from src.manifest import Manifest, now_str  # noqa: E402


def pick_pilot(rows: list[dict], n: int, rng: random.Random) -> list[str]:
    """Pilot: 그룹(Dataset/split) + 빈 TXT + 다중 BBox + 단일 BBox 가 골고루 들어가게."""
    buckets = defaultdict(list)
    for r in rows:
        cnt = r["original_bbox_count"]
        kind = "noTXT" if cnt == "" else ("empty" if cnt == "0" else ("multi" if int(cnt) >= 3 else "single"))
        buckets[(r["source_dataset"], r["original_split"], kind)].append(r["relative_path"])
    for b in buckets.values():
        rng.shuffle(b)
    chosen: list[str] = []
    while len(chosen) < n and any(buckets.values()):
        for key in sorted(buckets):
            if buckets[key] and len(chosen) < n:
                chosen.append(buckets[key].pop())
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", nargs="+", required=True)
    ap.add_argument("--pilot", type=int, default=0, help="Pilot 이미지 수 (0 이면 선정 안 함)")
    ap.add_argument("--force", action="store_true", help="기존 배분을 무시하고 PENDING 행 전부 재배분")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--work")
    a = ap.parse_args()
    paths = Paths(work_root=a.work)
    m = Manifest(paths.manifest)
    if not m.rows:
        raise SystemExit("Manifest 가 비어 있습니다. 01_build_manifest.py 를 먼저 실행하세요.")
    rng = random.Random(a.seed)
    workers = a.workers
    reviewer_of = {w: workers[(i + 1) % len(workers)] for i, w in enumerate(workers)}

    targets = [r for r in m.rows.values()
               if (not r["assignee"]) or (a.force and r["status"] == "PENDING")]
    groups = defaultdict(list)
    for r in targets:
        groups[(r["source_dataset"], r["original_split"])].append(r)
    load = {w: sum(1 for r in m.rows.values() if r["assignee"] == w and r not in targets) for w in workers}
    for key in sorted(groups):
        rows = groups[key]
        rng.shuffle(rows)
        for r in rows:
            w = min(workers, key=lambda x: (load[x], workers.index(x)))   # 가장 적게 받은 사람
            r["assignee"], r["reviewer"] = w, reviewer_of[w]
            r["updated_at"], r["updated_by"] = now_str(), "assign"
            load[w] += 1
    if a.pilot:
        for r in m.rows.values():
            r["pilot"] = ""
        for key in pick_pilot(list(m.rows.values()), a.pilot, rng):
            m.rows[key]["pilot"] = "1"
    m.save()
    print(f"배분 {len(targets)}장")
    for w in workers:
        n = sum(1 for r in m.rows.values() if r["assignee"] == w)
        p = sum(1 for r in m.rows.values() if r["assignee"] == w and r["pilot"] == "1")
        print(f"  {w:<8} 담당 {n:>4}장 (Pilot {p})  -> 검수자 {reviewer_of[w]}")


if __name__ == "__main__":
    main()
