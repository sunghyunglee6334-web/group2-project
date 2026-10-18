"""
03_build_split.py — 라벨 겹침 기준 Split (촬영 묶음 무시) + YOLO 폴더 생성

실행 (project8 폴더에서):
    python scripts/03_build_split.py              split + 폴더 생성
    python scripts/03_build_split.py --no-copy    CSV·요약만 (폴더 복사 건너뜀)

입력 : data/final/{images,labels}, manifest_final.csv   (원본, 건드리지 않음)
       data/final이 없으면 data/data/final을 찾음
출력 : (final 폴더와 같은 위치에)
         yolo/images/{train,val,test}, yolo/labels/{train,val,test}
         bridge_holdout/images, bridge_holdout/labels
       기존 yolo/, bridge_holdout/가 있으면 _old_split_<시각>/ 로 옮겨 둠 (지우지 않음)
       configs/dataset.yaml   (Bridge 제외)
       manifests/{split_manifest,train,val,test,bridge_holdout}.csv
       reports/split_summary.md

규칙
  [1] 라벨이 30% 이상 겹치는 사진끼리 묶음 → 묶음은 전부 train
      겹침 = 같은 class, 중심 x·y 차이 ≤ 이미지의 10%, 너비·높이 차이 ≤ 10%(상대)인 bbox 수
             / 두 파일 중 많은 bbox 수
  [2] 정상 김치(+ scene_type none) → 전부 train
  [3] 객체 단독 → train 80% / val 20% (test·bridge에는 넣지 않음)
  [4] 김치+객체 → train / val / test / bridge 남은 자리 채움
  [5] 장수 train 600 / val 75 / test 75 / bridge_holdout 150
  묶음에 안 들어간 사진은 희소 class부터 순서대로, (남은 자리 / 목표)가 가장 큰 split에 배정 → 결정적
"""
import argparse, csv, itertools, shutil, time
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ==================================================================
# 정책 값 — 여기만 고칩니다
# ==================================================================
SIZES = {"train": 600, "val": 75, "test": 75, "bridge_holdout": 150}
OVERLAP = 0.30          # [1] 라벨 겹침 비율 기준
TOL_CENTER = 0.10       # [1] 중심 차이 (이미지 크기 대비)
TOL_SIZE = 0.10         # [1] 너비·높이 차이 (상대)
OBJ_TRAIN_RATIO = 0.8   # [3] 객체 단독 train 비율 (나머지 val)
OBJ_SPLITS = ["train", "val"]   # [3] 객체 단독이 갈 수 있는 split (bridge도 넣으려면 "bridge_holdout" 추가)
NORMAL = {"normal_kimchi", "none"}
NAMES = {0: "leaf_paper", 1: "plastic_stone_metal", 2: "branch", 3: "insect",
         4: "rubber_glove_unused", 5: "disease_browning", 6: "green_onion_pepper"}
# ==================================================================
SPLITS = list(SIZES)


def find_data_root():
    for p in (PROJECT_ROOT / "data" / "final", PROJECT_ROOT / "data" / "data" / "final"):
        if (p / "labels").is_dir() and (p / "images").is_dir():
            return p
    raise SystemExit("data/final/{images,labels}를 찾지 못했습니다")


def load_boxes(path):
    out = []
    if path.exists():
        for line in path.read_text().split("\n"):
            p = line.split()
            if len(p) == 5:
                out.append((int(p[0]), *map(float, p[1:])))
    return out


def same_box(a, b):
    return (a[0] == b[0] and abs(a[1] - b[1]) <= TOL_CENTER and abs(a[2] - b[2]) <= TOL_CENTER
            and abs(a[3] - b[3]) <= TOL_SIZE * max(a[3], b[3])
            and abs(a[4] - b[4]) <= TOL_SIZE * max(a[4], b[4]))


def overlap(A, B):
    if not A or not B:
        return 0.0
    return sum(1 for a in A if any(same_box(a, b) for b in B)) / max(len(A), len(B))


def build_clusters(names, boxes):
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    pairs = []
    for x, y in itertools.combinations(names, 2):
        r = overlap(boxes[x], boxes[y])
        if r >= OVERLAP:
            pairs.append((x, y, r))
            parent[find(x)] = find(y)
    comp = defaultdict(list)
    for n in names:
        comp[find(n)].append(n)
    multi = sorted(sorted(v) for v in comp.values() if len(v) > 1)
    return {n: f"C{i:03d}" for i, c in enumerate(multi) for n in c}, pairs


def assign(items, quota, classes_of, class_freq, split_of):
    left = {s: q for s, q in quota.items() if q > 0}
    rarity = lambda n: (min((class_freq[c] for c in classes_of[n]), default=10**9), n)
    for n in sorted(items, key=rarity):
        s = max((s for s in left if left[s] > 0), key=lambda s: (left[s] / quota[s], -SPLITS.index(s)))
        split_of[n] = s
        left[s] -= 1


def export_folders(rows, img_of, lbl_dir, base):
    yolo, bridge = base / "yolo", base / "bridge_holdout"
    old = [p for p in (yolo, bridge) if p.exists()]
    if old:
        backup = base / f"_old_split_{time.strftime('%Y%m%d_%H%M%S')}"
        backup.mkdir()
        for p in old:
            shutil.move(str(p), str(backup / p.name))
        print(f"[6단계] 기존 {', '.join(p.name for p in old)} → {backup.relative_to(PROJECT_ROOT)} 로 옮김")
    dirs = {s: (yolo / "images" / s, yolo / "labels" / s) for s in ("train", "val", "test")}
    dirs["bridge_holdout"] = (bridge / "images", bridge / "labels")
    for d in dirs.values():
        for p in d:
            p.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(rows, 1):
        di, dl = dirs[r["split"]]
        src = img_of[r["stem"]]
        shutil.copy2(src, di / src.name)
        lbl = lbl_dir / f"{r['stem']}.txt"
        if lbl.exists():
            shutil.copy2(lbl, dl / lbl.name)
        else:
            (dl / lbl.name).write_text("")
        if i % 150 == 0:
            print(f"  … 복사 {i}/{len(rows)}", flush=True)
    for s, (di, dl) in dirs.items():
        ni, nl = len(list(di.iterdir())), len(list(dl.iterdir()))
        assert ni == nl == SIZES[s], (s, ni, nl)
    y = PROJECT_ROOT / "configs" / "dataset.yaml"
    rel = Path(shutil.os.path.relpath(yolo, y.parent)).as_posix()
    y.write_text("# 03_build_split.py가 생성 (라벨 겹침 기준 split · Bridge Holdout 제외)\n"
                 f"train: {rel}/images/train\nval: {rel}/images/val\ntest: {rel}/images/test\nnames:\n"
                 + "".join(f"  {k}: {v}\n" for k, v in NAMES.items()), encoding="utf-8")
    return yolo, bridge, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-copy", action="store_true", help="CSV·요약만 만들고 폴더 복사는 건너뜀")
    a = ap.parse_args()

    root = find_data_root()
    print(f"원본: {root.relative_to(PROJECT_ROOT)}")
    man = list(csv.DictReader(open(root / "manifest_final.csv", encoding="utf-8-sig")))
    img_of = {p.stem: p for p in (root / "images").iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}}
    for r in man:
        r["stem"] = Path(r["image_name"]).stem
        assert r["stem"] in img_of, f"이미지 없음: {r['image_name']}"
    boxes = {r["stem"]: load_boxes(root / "labels" / f"{r['stem']}.txt") for r in man}
    scene = {r["stem"]: r["scene_type"] for r in man}
    classes_of = {s: {b[0] for b in bs} for s, bs in boxes.items()}
    class_freq = Counter(c for cs in classes_of.values() for c in cs)
    assert len(man) == sum(SIZES.values()), f"전체 {len(man)}장 ≠ {sum(SIZES.values())}"

    # [1] 라벨 겹침 묶음
    cid, pairs = build_clusters([s for s in boxes if boxes[s]], boxes)
    split_of, reason = {}, {}
    for s in boxes:
        if scene[s] in NORMAL:
            split_of[s], reason[s] = "train", "정상 김치 → train"
        elif s in cid:
            split_of[s], reason[s] = "train", f"라벨 {OVERLAP:.0%}+ 겹침 묶음 {cid[s]} → train"

    obj = [s for s in boxes if scene[s] == "object_only"]
    kim = [s for s in boxes if scene[s] == "kimchi_with_target"]
    unknown = Counter(scene[s] for s in boxes if scene[s] not in NORMAL | {"object_only", "kimchi_with_target"})
    assert not unknown, f"알 수 없는 scene_type: {unknown}"

    # [3] 객체 단독
    obj_train = round(len(obj) * OBJ_TRAIN_RATIO)
    obj_fixed = sum(1 for s in obj if s in split_of)
    if obj_fixed > obj_train:
        raise SystemExit(f"객체 단독 묶음({obj_fixed}장)이 train 몫({obj_train}장)보다 많음")
    rest = len(obj) - obj_train
    others = [s for s in OBJ_SPLITS if s != "train"]
    obj_quota = {"train": obj_train - obj_fixed}
    for i, s in enumerate(others):
        obj_quota[s] = rest // len(others) + (1 if i < rest % len(others) else 0)
    assign([s for s in obj if s not in split_of], obj_quota, classes_of, class_freq, split_of)

    # [4] 김치+객체
    used = Counter(split_of.values())
    kim_quota = {sp: SIZES[sp] - used.get(sp, 0) for sp in SPLITS}
    kim_free = [s for s in kim if s not in split_of]
    if min(kim_quota.values()) < 0 or sum(kim_quota.values()) != len(kim_free):
        raise SystemExit(f"장수가 맞지 않음: 남은 자리 {kim_quota}, 남은 김치+객체 {len(kim_free)}장")
    assign(kim_free, kim_quota, classes_of, class_freq, split_of)
    for s in split_of:
        reason.setdefault(s, f"{scene[s]} 층화 배정")

    # [5] 검증
    cnt = Counter(split_of.values())
    assert cnt == Counter(SIZES), cnt
    assert all(split_of[x] == split_of[y] for x, y, _ in pairs), "겹침 쌍이 split을 넘나듦"

    rows = [{"image_name": r["image_name"], "stem": r["stem"], "split": split_of[r["stem"]],
             "scene_type": scene[r["stem"]], "cluster_id": cid.get(r["stem"], ""),
             "n_boxes": len(boxes[r["stem"]]), "classes": " ".join(map(str, sorted(classes_of[r["stem"]]))),
             "reason": reason[r["stem"]], "original_split": r["original_split"]} for r in man]

    mdir = PROJECT_ROOT / "manifests"
    mdir.mkdir(parents=True, exist_ok=True)
    cols = [k for k in rows[0] if k != "stem"]
    for name, sel in [("split_manifest", rows)] + [(sp, [r for r in rows if r["split"] == sp]) for sp in SPLITS]:
        with open(mdir / f"{name}.csv", "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader(); w.writerows(sel)

    L = ["# Split 요약", "", f"- 원본: `{root.relative_to(PROJECT_ROOT)}`",
         f"- 라벨 {OVERLAP:.0%}+ 겹침 쌍 {len(pairs)}개 → 묶음 {len(set(cid.values()))}개, {len(cid)}장 (전부 train)", "",
         "## split × scene_type", "", "| split | 김치+객체 | 객체 단독 | 정상 김치(+none) | 합계 |", "|---|---|---|---|---|"]
    for sp in SPLITS:
        c = Counter("normal" if scene[s] in NORMAL else scene[s] for s in split_of if split_of[s] == sp)
        L.append(f"| {sp} | {c['kimchi_with_target']} | {c['object_only']} | {c['normal']} | {cnt[sp]} |")
    L += ["", "## split별 class 포함 이미지 비율(%)", "", "| class | " + " | ".join(SPLITS) + " |",
          "|---|" + "---|" * len(SPLITS)]
    for c in sorted(class_freq):
        L.append(f"| {c} {NAMES.get(c, '')} | " + " | ".join(
            f"{100 * sum(1 for s in split_of if split_of[s] == sp and c in classes_of[s]) / cnt[sp]:.1f}"
            for sp in SPLITS) + " |")

    if not a.no_copy:
        print("[6단계] 이미지·라벨 복사 중…", flush=True)
        yolo, bridge, y = export_folders(rows, img_of, root / "labels", root.parent)
        L += ["", "## 생성된 폴더", "",
              f"- `{yolo.relative_to(PROJECT_ROOT)}/images|labels/train|val|test`",
              f"- `{bridge.relative_to(PROJECT_ROOT)}/images|labels`",
              f"- `{y.relative_to(PROJECT_ROOT)}`"]

    (PROJECT_ROOT / "reports" / "split_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
