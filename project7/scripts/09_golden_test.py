"""Golden Sample 기능시험: 프로그램이 좌표와 Class 를 망가뜨리지 않는지 확인.

임시 WORK 폴더에서 (실제 WORK 는 건드리지 않음)
  1) YOLO -> 픽셀 -> YOLO 왕복 오차 < 1e-6
  2) 여러 Zoom/Pan 상태에서 원본 -> 화면 -> 원본 왕복 오차 < 1e-6
  3) 수정 없이 저장 -> WORK TXT 가 RAW 와 바이트 단위로 동일
  4) BBox 추가 + Class 변경 + 삭제 -> 저장 -> 다시 불러오기 -> 동일
  5) RAW 파일이 바뀌지 않음

10.12 추가 사항)
테스트 실행 유효성을 위해 대상이 0 장인 경우 -> 경고 문구 추가
화면 변환 검사 시 박스 0 인 경우 -> 검사 생략 문구 추가
입력 라벨 문제로 수행하지 못한 검사는 PASS 가 아니라 SKIP과 사유를 기록

    python scripts/09_golden_test.py --n 20                 # 무작위 20장
    python scripts/09_golden_test.py --list golden.txt      # 지정 목록(relative_path 한 줄씩)
"""
import argparse
import hashlib
import random
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import ACTIVE_CLASS_IDS, REPORT_DIR, Paths  # noqa: E402
from src.bbox.session import LabelSession, canonical  # noqa: E402
from src.bbox.view import ViewTransform  # noqa: E402
from src.yolo.yolo_io import parse_line, pixel_to_yolo, yolo_to_pixel  # noqa: E402


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else "-"


def test_image(
    sess: LabelSession, key: str
) -> tuple[list[str], list[str]]:
    """이미지 한 장의 기능시험을 수행하고 (실패, 생략 사유)를 반환하는 tuple 추가."""
    errs = []
    skips = []  # [추가] 검사 생략 사유 / 10.12
    
    sess.view_keys = [key]
    cur = sess.load(0)
    rec = cur.rec
    raw_lbl = rec.raw_label(sess.paths)
    raw_hash = (md5(rec.raw_image(sess.paths)), md5(raw_lbl))


    # 1) YOLO 왕복
    # [변경] 검사하지 못한 이유와 파싱 오류를 기록
    if cur.raw_text is None:
        # 중복 실패 메시지는 추가하지 않고 생략 사유만 기록
        skips.append("YOLO 왕복: 예상 경로에 RAW TXT가 없어 생략")

    elif not cur.raw_text.strip():
        # 객체 없는 이미지의 빈 TXT는 정상
        skips.append("YOLO 왕복: 빈 라벨 - 검사할 좌표 없음")

    else:
        for line_no, line in enumerate(
            cur.raw_text.splitlines(), start=1
        ):
            v, e = parse_line(line)
            
            if e:
                skips.append(f"YOLO 왕복: {line_no}번 행 파싱 오류")
                continue

            back = pixel_to_yolo(yolo_to_pixel(*v, cur.width, cur.height), cur.width, cur.height)

            if max(abs(x - y) for x, y in zip(v[1:], back[1:])) > 1e-6:
                errs.append(f"YOLO 왕복 오차: {line}")

    # 2) 화면 변환 왕복
    if not cur.boxes:
        skips.append("화면 변환 왕복: 검사할 박스 없음")  # 박스가 없는 경우 확인용 추가    / 10.12

    vt = ViewTransform()
    vt.fit(cur.width, cur.height, 1200, 800)

    for factor, px, py in ((2, 300, 200), (3, 900, 700), (0.5, 10, 10), (8, 600, 400)):
        vt.zoom_at(factor, px, py)
        vt.pan(37, -21)
        for b in cur.boxes:
            cx, cy = vt.to_canvas(b.x1, b.y1)
            ix, iy = vt.to_image(cx, cy)
            if abs(ix - b.x1) > 1e-6 or abs(iy - b.y1) > 1e-6:
                errs.append(f"화면 변환 왕복 오차 (zoom {vt.scale:.2f})")
                break

    # 3) 무수정 저장 = RAW 와 동일
    if cur.raw_text is not None and not cur.raw_had_errors:         
        sess.save("PASS")                                           
        if rec.work_label(sess.paths).read_bytes() != raw_lbl.read_bytes():
            errs.append("무수정 저장 결과가 RAW 와 다름")

    # [추가] 입력 라벨이 없어 수행하지 못한 검사 기록    / 10.12
    else:
        if cur.raw_text is None:
            skips.append(
                "무수정 저장 비교: 예상 경로에 RAW TXT가 없어 생략"
            )
        else:
            skips.append(
                "무수정 저장 비교: RAW 라벨 읽기·해석 오류로 생략"
            )

    # 4) 편집 -> 저장 -> 재로드
    cur = sess.load(0)
    w, h = cur.width, cur.height
    sess.add_box(ACTIVE_CLASS_IDS[0], w * 0.1, h * 0.1, w * 0.2, h * 0.25)
    sess.set_box_class(len(cur.boxes) - 1, ACTIVE_CLASS_IDS[-1])

    if len(cur.boxes) > 1:
        sess.delete_box(0)
    expect = canonical(cur.boxes, w, h)
    st = sess.save("PASS")

    if st != "EDITED":
        errs.append(f"수정 후 PASS 요청이 EDITED 로 바뀌지 않음 ({st})")
    again = sess.load(0)

    if canonical(again.boxes, w, h) != expect:
        errs.append("저장 후 재로드 결과가 다름")

    # 5) RAW 보존
    if (md5(rec.raw_image(sess.paths)), md5(raw_lbl)) != raw_hash:
        errs.append("RAW 가 변경됨!!")
    return errs, skips


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--list")
    ap.add_argument("--raw")
    a = ap.parse_args()
    raw = Paths(a.raw).raw

    with tempfile.TemporaryDirectory() as tmp:
        sess = LabelSession(Paths(raw, tmp), worker="golden_test")
        keys = [r.rel_image for r in sess.records]

        if a.list:
            keys = [k.strip() for k in Path(a.list).read_text(encoding="utf-8").splitlines() if k.strip()]
        else:
            random.seed(0)          # 랜덤 고정 씨드값 설정
            keys = random.sample(keys, min(a.n, len(keys)))

        # [추가] 검사 대상이 없으면(=0) 성공으로 처리하지 않고 에러 문구와 함께 종료     / 10.12
        if not keys:
            print(
                "ERROR: 검사 대상이 없습니다. "
                "--raw 경로의 이미지와 --list 목록을 확인하세요.",
                file=sys.stderr,
            )
            return 2

        lines, fails = [], 0
        for k in keys:
            # [일부 수정] 두 목록을 각각 받음     / 10.12
            errs, skips = test_image(sess, k)
            fails += bool(errs)

            # [추가] 생략 사유를 출력 내용에 포함    / 10.12
            status = "FAIL" if errs else "PASS"
            details = errs + [f"SKIP — {reason}" for reason in skips]

            lines.append(f"{status}  {k}  {'; '.join(details)}")
            print(lines[-1])

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    (REPORT_DIR / "golden_test.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nGolden Sample {len(keys)}장 중 실패 {fails}장 -> reports/golden_test.txt")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
