"""학습된 YOLO 모델을 같은 기준으로 평가하는 공통 모듈 (④ Evaluation 담당).
Baseline · Improved · Final 모델 모두 이 파일로 평가한다."""
import csv
from pathlib import Path

VALID_SPLITS = ("val", "test")

# 평가 전 입력 확인
def check_inputs(model_path, data_yaml, split, allow_test=False):
    
    # (1) Weight 파일 존재 확인
    if not Path(model_path).is_file():
        raise FileNotFoundError(f"Weight 파일이 없습니다: {model_path}")
    # (2) dataset.yaml 존재 확인
    if not Path(data_yaml).is_file():
        raise FileNotFoundError(f"dataset.yaml 이 없습니다: {data_yaml}")
    # (3) split 값 확인   
    if split not in VALID_SPLITS:
        raise ValueError(f"split 은 {VALID_SPLITS} 중 하나여야 합니다. 받은 값: {split!r}")
    # (4) test split이 allow_test=False 시 막는다
    if split == "test" and not allow_test:
        raise PermissionError(
            "Frozen Test 는 Final Model 을 정한 뒤에만 엽니다. "
            "정말 최종 평가라면 allow_test=True 를 넣어 주세요."
        )

# 평가 실행
def evaluate_detector(
    model_path: str,
    data_yaml: str,
    split: str = "val",
    imgsz: int = 640,
    allow_test: bool = False,
):
    # 평가 전 입력 확인
    check_inputs(model_path, data_yaml, split, allow_test)

    from ultralytics import YOLO  # 실제 평가할 때만 불러온다
    model = YOLO(model_path)
    return model.val(
        data=data_yaml,
        split=split,
        imgsz=imgsz,
        plots=True,
    )

# 평가 결과 정리: 전체 성능 4개
def summarize_overall(metrics, digits=4):
    box = metrics.box
    return {
        "precision": round(float(box.mp), digits),
        "recall":    round(float(box.mr), digits),
        "map50":     round(float(box.map50), digits),
        "map50_95":  round(float(box.map), digits),
    }

# 평가 결과 정리: Class별 성능
def summarize_per_class(metrics, digits=4):
    box = metrics.box
    names = metrics.names

    # 안내표: {Class 번호: 성적표 안 위치}  예) {0:0, 1:1, 2:2, 3:3, 5:4, 6:5}
    position = {int(class_id): i for i, class_id in enumerate(box.ap_class_index)}

    rows = []
    for class_id in sorted(names):             # ② Class 0~6 을 순서대로
        row = {"class_id": class_id, "class_name": names[class_id]}

        if class_id in position:               # ③ 성적이 있으면 꺼내고
            p, r, ap50, ap = box.class_result(position[class_id])
            row["precision"] = round(float(p), digits)
            row["recall"] = round(float(r), digits)
            row["map50"] = round(float(ap50), digits)
            row["map50_95"] = round(float(ap), digits)
        else:                                  # ④ 없으면 N/A
            row["precision"] = row["recall"] = row["map50"] = row["map50_95"] = "N/A"

        rows.append(row)
    return rows


def save_metrics_csv(rows, out_path):
    if isinstance(rows, dict):
        rows = [rows]
    # 저장할 게 없으면 멈춤
    if not rows:
        raise ValueError("저장할 결과가 없습니다 (rows 가 비어 있음).")

    # reports/ 폴더가 없으면 만든다
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True) 

    columns = list(rows[0].keys())      # 첫 줄의 키 = 컬럼 이름
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()            # 컬럼 이름 줄
        writer.writerows(rows)          # 내용 줄들
    return out_path