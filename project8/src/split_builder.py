"""
split_builder.py — 교과 8 데이터셋 역할 분할 도구 (Data 담당)

[1. 왜 필요한가]
  교과 7 FINAL Dataset을 아래 4가지 역할로 나눈다.
    train          : 모델이 공부할 데이터
    val            : 개발 중 비교할 데이터
    test           : 교과 8 마지막 시험 데이터 (Frozen Test)
    bridge_holdout : 교과 14를 위해 보존할 데이터

[2. 입력]
  교과 7 FINAL Dataset + Dataset Manifest(CSV)
  Manifest 필수 열: source_dataset, original_split, scene_type, capture_group

[4. 처리 순서]
  STEP 1  Manifest 읽기
  STEP 2  기존 source / split 확인
  STEP 3  유사 촬영 그룹 확인 (+ 같은 파일 중복 확인)
  STEP 4  Split 정책 적용
          (25장이 아닌 그룹은 Train 고정)
          4-1 Bridge Holdout → 4-2 Frozen Test → 4-3 Validation → 4-4 Train(나머지)
  STEP 5  각 역할의 분포 확인 (Class / scene_type)
  STEP 6  성공 기준 검사
  STEP 7  결과 저장 + 기록

[5. 결과]
  split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
  + split_report.md (10번 기록 항목)

[TODO 표시]
  아직 정하지 않은 기준선은 모두 "TODO(기준선)"으로 표시했다.
  이 문자열로 검색하면 나중에 확인할 곳을 한 번에 찾을 수 있다.

사용 예:
  python group_candidates.py --manifest manifest_final.csv --out manifest_grouped.csv
  python split_builder.py --manifest manifest_grouped.csv --labels final/labels --out splits
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import csv
import hashlib
import random

# =====================================================================
# 설정
# =====================================================================

# TODO(기준선): 교과 7 FINAL Dataset 버전 이름 확정 (예: "v1.0-final")
DATASET_VERSION = "TODO"

ROLES = ["train", "val", "test", "bridge_holdout"]

# Manifest 열 이름 후보 (왼쪽: 코드에서 쓰는 이름, 오른쪽: CSV에서 찾을 열 이름, 앞쪽 우선)
# 교과 7 FINAL Manifest(manifest_final.csv) 열 이름을 먼저 찾고, 없으면 가상 Manifest 이름을 찾는다
COL_CANDIDATES = {
    "image_id": ["image_name", "image_id"],               # 파일 이름
    "image_path": ["relative_path", "image_path"],        # 이미지 경로 (있으면 중복 검사)
    "label_path": ["label_relative_path", "label_path"],  # 라벨 경로 (있으면 Class 분포)
    "source_dataset": ["source_dataset"],
    "original_split": ["original_split"],
    "scene_type": ["scene_type"],
    "capture_group": ["capture_group"],                   # group_candidates.py가 추가
}
COL = {}   # read_manifest()에서 실제 열 이름으로 채운다
REQUIRED = ["image_id", "source_dataset", "original_split", "scene_type", "capture_group"]

SPLIT_POLICY = {
    # TODO(기준선): 정책 이름과 방식 확정 (지금은 촬영 그룹 단위 무작위 분할)
    "name": "group_random_v0",
    "seed": 42,
    # 팀 결정 (2026-10-14): Train 600 / Val 75 / Frozen Test 75 / Bridge 150 (900장 기준)
    "ratios": {"train": 600 / 900, "val": 75 / 900, "test": 75 / 900, "bridge_holdout": 150 / 900},
    # 기존 validation은 쓰지 않음 (누수 위험 + 수량 불일치, docs/split_policy.md 1장)
    "keep_original_val": False,
    "min_test_images": 75,
    # 크기가 이 값이 아닌 그룹은 Train에 고정 (docs/split_policy.md 0장)
    # TODO(기준선): 25장 블록 가설 확정 후 유지 여부 결정. None이면 사용 안 함
    "fixed_block_size": 25,
}

VAL_NAMES = {"val", "valid", "validation"}


# =====================================================================
# STEP 1. Manifest 읽기
# =====================================================================
def read_manifest(manifest_path: Path, root: Path = None, labels_dir: Path = None):
    """root: 이미지·라벨 상대 경로의 기준 폴더 (기본: Manifest가 있는 폴더)
    labels_dir: 라벨 txt가 한 폴더에 모여 있을 때 그 폴더 (있으면 label_path 대신 사용)"""
    with open(manifest_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = [{k: (v or "").strip() for k, v in r.items()} for r in reader]

    # 실제 열 이름 정하기
    COL.clear()
    for key, cands in COL_CANDIDATES.items():
        COL[key] = next((c for c in cands if c in fieldnames), "")
    missing = [COL_CANDIDATES[k][0] for k in REQUIRED if not COL[k]]
    if missing:
        hint = " (capture_group은 group_candidates.py로 먼저 추가)" if "capture_group" in missing else ""
        raise SystemExit(f"[오류] Manifest에 필수 열이 없습니다: {missing}{hint}")

    root = root or manifest_path.parent
    for r in rows:
        img = r.get(COL["image_path"], "") if COL["image_path"] else ""
        r["_image_path"] = (root / img) if img else None
        if labels_dir:
            r["_label_path"] = labels_dir / (Path(r[COL["image_id"]]).stem + ".txt")
        else:
            lbl = r.get(COL["label_path"], "") if COL["label_path"] else ""
            r["_label_path"] = (root / lbl) if lbl else None
    return rows, fieldnames


# =====================================================================
# STEP 2. 기존 source / split 확인
# =====================================================================
def check_existing_split(rows):
    src = Counter(r[COL["source_dataset"]] for r in rows)
    org = Counter(r[COL["original_split"]] for r in rows)
    has_val = any(s.lower() in VAL_NAMES for s in org)

    print("\n[STEP 2] 기존 source / split")
    print("  source_dataset :", dict(src))
    print("  original_split :", dict(org))
    print("  기존 validation 정보:", "있음" if has_val else "없음")
    return has_val


# =====================================================================
# STEP 3. 유사 촬영 그룹 확인 (+ 같은 파일 중복)
# =====================================================================
def file_hash(path):
    if path is None or not path.exists():
        return None
    return hashlib.md5(path.read_bytes()).hexdigest()


def build_groups(rows):
    """같은 capture_group은 반드시 같은 역할로 보내기 위해 그룹으로 묶는다.

    TODO(기준선): '유사 이미지' 판단 기준 확정
      - 지금은 capture_group 열 + 파일 내용이 완전히 같은 경우만 같은 그룹으로 본다.
      - 나중에 이미지 유사도(pHash 등) 기준을 추가할 수 있다.
    TODO(기준선): capture_group이 비어 있는 이미지를 어떻게 처리할지
      - 지금은 그 이미지 혼자 하나의 그룹으로 취급한다.
    """
    problems = []

    # 같은 image_id 중복
    id_count = Counter(r[COL["image_id"]] for r in rows)
    dup_ids = [i for i, c in id_count.items() if c > 1]
    if dup_ids:
        problems.append(f"같은 image_id 중복 {len(dup_ids)}건: {dup_ids[:5]}")

    # 그룹 키 정하기
    empty_group = 0
    for r in rows:
        g = r[COL["capture_group"]]
        if not g:
            g = f"__single__{r[COL['image_id']]}"
            empty_group += 1
        r["_group"] = g
        r["_hash"] = file_hash(r["_image_path"])
    if empty_group:
        problems.append(f"capture_group이 비어 있는 이미지 {empty_group}장 (각각 단독 그룹 처리)")

    # 파일 내용이 같은 이미지가 서로 다른 그룹에 있으면 두 그룹 전체를 하나로 합친다
    # (한 장만 옮기면 원래 그룹이 두 역할로 쪼개지기 때문)
    # TODO(기준선): 같은 파일 중복을 합칠지, 하나만 남기고 제외할지 결정
    parent = {}

    def find(g):
        parent.setdefault(g, g)
        while parent[g] != g:
            g = parent[g]
        return g

    first_group_of_hash = {}
    dup_files = 0
    for r in rows:
        h = r["_hash"]
        if h is None:
            continue
        if h in first_group_of_hash:
            parent[find(r["_group"])] = find(first_group_of_hash[h])
            dup_files += 1
        else:
            first_group_of_hash[h] = r["_group"]
    for r in rows:
        r["_group"] = find(r["_group"])
    if dup_files:
        problems.append(f"내용이 같은 이미지 파일 {dup_files}장 (해당 그룹끼리 합침)")

    groups = defaultdict(list)
    for r in rows:
        groups[r["_group"]].append(r)

    sizes = sorted((len(v) for v in groups.values()), reverse=True)
    print("\n[STEP 3] 유사 촬영 그룹")
    print(f"  그룹 수: {len(groups)}  /  가장 큰 그룹: {sizes[0] if sizes else 0}장")
    for p in problems:
        print("  ⚠", p)
    return groups, problems


# =====================================================================
# STEP 4. Split 정책 적용
# =====================================================================
def _fill(role, remaining, groups, target, assignment):
    """남은 그룹을 앞에서부터 목표 장수에 가깝게 role에 배정한다.
    그룹 단위로 넣기 때문에 목표와 정확히 같지는 않을 수 있다.
    그룹을 넣었을 때 목표를 그룹 크기의 절반 넘게 초과하면 건너뛰고 다음 역할로 넘긴다.
    TODO(기준선): 목표 장수 허용 오차 기준 확정"""
    taken, left = 0, []
    for g in remaining:
        size = len(groups[g])
        if taken + size / 2 <= target:
            assignment[g] = role
            taken += size
        else:
            left.append(g)
    return left


# 배정 순서 (docs/split_policy.md 5장): Bridge → Frozen Test → Validation → Train(나머지)

def decide_bridge(remaining, groups, target, assignment):
    # TODO(기준선): Bridge Holdout 결정 기준 (교과 14에서 무엇을 확인할지에 맞춰 정하기)
    return _fill("bridge_holdout", remaining, groups, target, assignment)


def decide_test(remaining, groups, target, assignment):
    # TODO(기준선): Frozen Test 결정 기준 (object_only 1 + 김치 2, Class 6 포함 여부)
    return _fill("test", remaining, groups, target, assignment)


def decide_val(remaining, groups, target, assignment):
    # TODO(기준선): Validation 결정 기준 (object_only 1 + 김치 2, 서로 다른 촬영일)
    return _fill("val", remaining, groups, target, assignment)


def decide_train(remaining, groups, assignment):
    # Train = 나머지 전부
    for g in remaining:
        assignment[g] = "train"
    return []


def apply_split_policy(groups, policy, has_val):
    rng = random.Random(policy["seed"])
    group_ids = sorted(groups)          # 정렬 후 섞어야 매번 같은 결과가 나온다
    rng.shuffle(group_ids)

    total = sum(len(v) for v in groups.values())
    targets = {r: round(total * policy["ratios"][r]) for r in ROLES}
    assignment = {}

    # 크기가 기준 블록과 다른 그룹은 Train 고정
    size = policy.get("fixed_block_size")
    if size:
        fixed = [g for g in group_ids if len(groups[g]) != size]
        for g in fixed:
            assignment[g] = "train"
        group_ids = [g for g in group_ids if g not in assignment]
        if fixed:
            print(f"\n  {size}장이 아닌 그룹 {len(fixed)}개({sum(len(groups[g]) for g in fixed)}장) → Train 고정")

    # 기존 validation 유지 옵션
    if policy["keep_original_val"] and has_val:
        kept = [g for g in group_ids
                if all(r[COL["original_split"]].lower() in VAL_NAMES for r in groups[g])]
        for g in kept:
            assignment[g] = "val"
        targets["val"] -= sum(len(groups[g]) for g in kept)
        group_ids = [g for g in group_ids if g not in assignment]

    remaining = decide_bridge(group_ids, groups, targets["bridge_holdout"], assignment)
    remaining = decide_test(remaining, groups, targets["test"], assignment)
    remaining = decide_val(remaining, groups, max(targets["val"], 0), assignment)
    decide_train(remaining, groups, assignment)

    for g, members in groups.items():
        for r in members:
            r["split_role"] = assignment[g]

    print("\n[STEP 4] Split 정책 적용:", policy["name"])
    print("  목표 장수:", targets)
    return assignment


# =====================================================================
# STEP 5. 각 역할의 분포 확인
# =====================================================================
def read_classes(label_path):
    """YOLO 라벨에서 Class 번호 목록을 읽는다. 라벨이 없으면 None."""
    if label_path is None or not label_path.exists():
        return None
    classes = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts:
            classes.append(parts[0])
    return classes


def check_distribution(rows, policy):
    count = Counter(r["split_role"] for r in rows)
    class_dist = {role: Counter() for role in ROLES}     # 객체(박스) 수
    scene_dist = {role: Counter() for role in ROLES}
    has_label_info = False

    for r in rows:
        role = r["split_role"]
        scene_dist[role][r[COL["scene_type"]]] += 1
        classes = read_classes(r["_label_path"])
        if classes is not None:
            has_label_info = True
            class_dist[role].update(classes)
            if not classes:
                class_dist[role]["(배경)"] += 1          # 빈 라벨 이미지 수

    warnings = []
    all_classes = set().union(*class_dist.values()) - {"(배경)"}
    for role in ("val", "test"):
        for c in sorted(all_classes):
            if class_dist[role][c] == 0:
                warnings.append(f"Class {c} 가 {role} 에 없음")

    for role in ROLES:
        if count[role] == 0:
            warnings.append(f"{role} 가 0장")
    if count["test"] < policy["min_test_images"]:
        warnings.append(f"Test가 너무 작음 ({count['test']}장 < 최소 {policy['min_test_images']}장)")

    all_scenes = set().union(*scene_dist.values())
    for role in ("val", "test"):
        for s in sorted(all_scenes):
            if scene_dist[role][s] == 0:
                warnings.append(f"scene_type '{s}' 가 {role} 에 없음")
    for s in sorted(all_scenes):
        roles_with = [role for role in ROLES if scene_dist[role][s] > 0]
        if len(roles_with) == 1:
            warnings.append(f"scene_type '{s}' 가 {roles_with[0]} 에만 있음")

    if not has_label_info:
        warnings.append("라벨 경로 정보가 없어 Class 분포를 확인하지 못함")

    print("\n[STEP 5] 역할별 분포")
    for role in ROLES:
        print(f"  {role:15s} {count[role]:4d}장 | Class {dict(class_dist[role])} | scene {dict(scene_dist[role])}")
    for w in warnings:
        print("  ⚠", w)
    return count, class_dist, scene_dist, warnings


# =====================================================================
# STEP 6. 성공 기준 검사
# =====================================================================
def validate(rows):
    results = []

    # 1) 모든 이미지가 정확히 하나의 역할에 속하는가
    roles_of_id = defaultdict(set)
    for r in rows:
        roles_of_id[r[COL["image_id"]]].add(r.get("split_role"))
    bad = [i for i, s in roles_of_id.items() if len(s) != 1 or not s <= set(ROLES)]
    results.append(("모든 이미지가 하나의 역할에만 속함", not bad, f"문제 {len(bad)}건"))

    # 2)·3)은 이미지 파일 내용(해시)으로 비교한다.
    #    이미지를 하나도 못 읽었으면 ok=None (확인 못 함) — 통과로 표시하지 않는다.
    hashed = sum(1 for r in rows if r["_hash"])
    no_image = f"확인 못 함 — 이미지 파일을 읽지 못함 ({hashed}/{len(rows)}장), --root 지정 필요"

    def hashes(roles):
        return {r["_hash"] for r in rows if r["split_role"] in roles and r["_hash"]}

    # 2) Train과 Frozen Test에 같은 이미지가 없는가
    overlap = hashes({"train"}) & hashes({"test"})
    ok = (not overlap) if hashed else None
    results.append(("Train과 Frozen Test에 같은 이미지 없음", ok, f"겹침 {len(overlap)}건" if hashed else no_image))

    # 3) Bridge Holdout이 다른 역할과 겹치지 않는가
    overlap = hashes({"bridge_holdout"}) & hashes({"train", "val", "test"})
    ok = (not overlap) if hashed else None
    results.append(("Bridge Holdout이 다른 역할과 겹치지 않음", ok, f"겹침 {len(overlap)}건" if hashed else no_image))

    # 4) 같은 촬영 그룹이 여러 역할에 섞이지 않는가
    roles_of_group = defaultdict(set)
    for r in rows:
        roles_of_group[r[COL["capture_group"]] or r["_group"]].add(r["split_role"])
    # (중복 파일 때문에 합쳐진 그룹도 원래 capture_group 기준으로 다시 확인된다)
    mixed = [g for g, s in roles_of_group.items() if len(s) > 1]
    results.append(("같은 촬영 그룹이 여러 역할에 섞이지 않음", not mixed, f"섞인 그룹 {mixed[:5]}"))

    print("\n[STEP 6] 성공 기준")
    for name, ok, detail in results:
        print("  " + mark(ok) + f" {name}" + ("" if ok else f" — {detail}"))
    return results


def mark(ok):
    return "✅" if ok else ("⚪" if ok is None else "❌")


# =====================================================================
# STEP 7. 결과 저장 + 기록
# =====================================================================
def save_outputs(rows, fieldnames, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = fieldnames + ["split_role"]

    def write(path, subset):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(subset)

    write(out_dir / "split_manifest.csv", rows)
    for role in ROLES:
        write(out_dir / f"{role}.csv", [r for r in rows if r["split_role"] == role])


def write_report(out_dir, policy, count, class_dist, scene_dist, warnings, problems, results):
    lines = [
        "# Split 기록",
        "",
        f"- Dataset Version: {DATASET_VERSION}",
        f"- Split 정책: {policy['name']} (seed={policy['seed']})",
        f"- 비율: {policy['ratios']}",
        f"- 기존 validation 유지: {policy['keep_original_val']}",
        "",
        "## 수량",
        "| 역할 | 장수 |",
        "|---|---|",
    ]
    lines += [f"| {role} | {count[role]} |" for role in ROLES]
    lines += [f"| 합계 | {sum(count.values())} |", "", "## Class 분포 (객체 수, (배경)=빈 라벨 이미지 수)"]
    lines += [f"- {role}: {dict(sorted(class_dist[role].items()))}" for role in ROLES]
    lines += ["", "## scene_type 분포"]
    lines += [f"- {role}: {dict(sorted(scene_dist[role].items()))}" for role in ROLES]
    lines += ["", "## 성공 기준"]
    lines += [f"- {mark(ok)} {name}" + ("" if ok else f" — {d}") for name, ok, d in results]
    lines += ["", "## 확인 필요 사항"]
    lines += [f"- {p}" for p in problems + warnings] or ["- 없음"]
    (out_dir / "split_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="교과 8 데이터셋 역할 분할 도구")
    parser.add_argument("--manifest", required=True, help="Dataset Manifest CSV")
    parser.add_argument("--out", default="splits", help="결과 저장 폴더")
    parser.add_argument("--root", help="이미지·라벨 상대 경로의 기준 폴더 (기본: Manifest 폴더)")
    parser.add_argument("--labels", help="라벨 txt가 모여 있는 폴더 (있으면 이 폴더에서 라벨을 읽음)")
    args = parser.parse_args()

    manifest = Path(args.manifest)
    if not manifest.exists():
        raise SystemExit(f"[오류] Manifest가 없습니다: {manifest}")
    root = Path(args.root) if args.root else None
    labels_dir = Path(args.labels) if args.labels else None
    if labels_dir and not labels_dir.is_dir():
        raise SystemExit(f"[오류] 라벨 폴더가 없습니다: {labels_dir}")

    rows, fieldnames = read_manifest(manifest, root, labels_dir)                # STEP 1
    print(f"[STEP 1] Manifest 읽기: {len(rows)}장")
    has_val = check_existing_split(rows)                                        # STEP 2
    groups, problems = build_groups(rows)                                       # STEP 3
    apply_split_policy(groups, SPLIT_POLICY, has_val)                           # STEP 4
    count, class_dist, scene_dist, warnings = check_distribution(rows, SPLIT_POLICY)  # STEP 5
    results = validate(rows)                                                    # STEP 6

    out_dir = Path(args.out)                                                    # STEP 7
    save_outputs(rows, fieldnames, out_dir)
    write_report(out_dir, SPLIT_POLICY, count, class_dist, scene_dist, warnings, problems, results)
    print(f"\n[STEP 7] 저장 완료: {out_dir}/")


if __name__ == "__main__":
    main()