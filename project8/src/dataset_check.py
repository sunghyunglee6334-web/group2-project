"""이미지 · YOLO TXT 짝 맞추기와 TXT 검사 (02 · 03 에서 사용)"""
from src.project_config import CLASS_NAMES, IMG_EXTS


def list_images(img_dir):
    return sorted(p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS)


def read_label(lbl_path):
    """YOLO TXT 한 개 읽기 -> (Class 번호 목록, 문제 목록). 빈 TXT = 배경 이미지 (정상)."""
    classes = []
    problems = []
    for i, line in enumerate(lbl_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            problems.append(("bad_format", f"{i}행 값 개수 {len(parts)} (5 이어야 함)"))
            continue
        try:
            cls = int(parts[0])
            coords = [float(v) for v in parts[1:]]
        except ValueError:
            problems.append(("bad_format", f"{i}행 숫자가 아닌 값"))
            continue
        if cls not in CLASS_NAMES:
            problems.append(("class_out_of_range", f"{i}행 Class {cls} (0~6 범위 밖)"))
        if any(not 0.0 <= v <= 1.0 for v in coords):
            problems.append(("coord_out_of_range", f"{i}행 좌표 {coords}"))
        classes.append(cls)
    return classes, problems
