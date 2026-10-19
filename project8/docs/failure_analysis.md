# Failure Analysis Hypothesis

> ⚠️ **옛 Split(v1) 기준 · 참고용**
> 이 문서의 숫자는 확정 Split(v4-B)이 아니라 이전 Split(v1, `kimchi_v1`) 기준이에요.
>
> | 항목 | 이 문서 (v1) | 확정 Split (v4-B) |
> |---|---|---|
> | 장수 | Train 600 / Val 75 | Train 609 / Val 66 / Test 75 / Bridge 150 |
> | Baseline (Val) | P 0.890 · R 0.592 · mAP50 0.658 | R 0.444 (v4-A 누수 상태에서는 0.781) |
>
> - "작은 이물 FN 36%"(EXP001 시작 근거)도 **v1 Val 75장 기준** 값이에요.
>   v4-B에서 같은 분석을 다시 하면 숫자가 달라질 수 있어요.
> - v4-B 기준 한계점: `docs/split_report.md`, `limitations.md`
> - Class 6(파·고추)·이물만 장면(T17)은 v4-B에서 **평가 불가**예요.

## 1. 분석 대상

- Model: baseline_v1 (YOLO11n)
- Weight: `models/baseline/baseline_best.pt`
- 학습 조건: imgsz 640 · batch 8 · epochs 70 · patience 30 · seed 42
- Dataset Version: kimchi_v1
- 분석 Split: **Validation 75장** (정답 객체 318개) — Frozen Test · Bridge Holdout은 보지 않음
- 판정 기준: conf ≥ 0.25 · IoU ≥ 0.5 + 같은 Class = TP · 확신도 높은 순 1:1 매칭 (`src/failure_analyzer.py`)
- 전체 실패: FP 93 · FN 63 · CLASS 17 · BBOX 17 (75장 중 57장에 실패)
- 대표 실패 사례: 18건 (FN 6 · FP 5 · CLASS 4 · BBOX 3) → `reports/failure_analysis.csv`, `demo/failure_analysis/`
- 성능: mAP50 0.658 · mAP50-95 0.505 · Precision 0.890 · Recall 0.592 (07, YOLO 공식 지표)
- 참고: main `val.csv`의 eval_exclude 4장(T17_V pHash 중복)은 이번 숫자에 포함되어 있음. 대표 사례에서는 제외함

## 2. 주요 실패 패턴

### Pattern 1 — 작은 이물 FN

관찰:
- 작은 이물일수록 많이 놓쳤습니다. 놓친 비율 small 36% (37/103) · medium 22% (20/91) · large 5% (6/124).
- leaf_paper small은 10개 중 8개, branch small은 69개 중 18개를 놓쳤습니다.

근거:
- `reports/fn_by_size.csv` (Split과 같은 크기 기준: 긴 변 640px 기준 √넓이, Class별 1/3)
- 대표 이미지: `demo/failure_analysis/fn_small_leaf_paper_01.jpg`, `fn_small_leaf_paper_02.jpg`, `fn_branch_01.jpg`, `fn_plastic_01.jpg`
- 맞힌 박스(TP)의 IoU 중앙값은 0.920 → 찾기만 하면 위치는 정확함. 문제는 "위치"가 아니라 "찾기"

### Pattern 2 — Class 5 disease_browning 미검출

관찰:
- Class 5 정답 14개 중 FN 11개, CLASS 3개. 모델이 Class 5로 예측한 박스가 0개입니다 (Recall 0).
- 위치를 찾은 3개(small 1 · large 2)도 branch나 plastic_stone_metal로 불렀습니다.

근거:
- `reports/class5_cases.csv`, `reports/fn_by_size.csv` (small 8/9 · medium 3/3 놓침)
- Train의 Class 5 객체 170개, 그중 60.6%가 small
- 대표 이미지: `demo/failure_analysis/fn_disease_browning_01.jpg`, `class_browning_01.jpg`

### Pattern 3 — 김치 장면의 FP (헛박스)

관찰:
- FP 93개 중 75개가 kimchi_with_target 장면, 80개가 IoU 0(정답과 전혀 안 겹침)입니다.
- 정상 김치(250410_155901509386.jpg)에서도 plastic_stone_metal FP 2개(0.469, 0.414)가 나왔습니다.

근거:
- `reports/failure_summary.csv`, `reports/iou_by_box.csv`
- 대표 이미지: `demo/failure_analysis/fp_kimchi_01.jpg` ~ `03.jpg`, `fp_normal_kimchi_01.jpg`
- 김치 조각·줄기를 이물로 착각한 것으로 보임 `[사진 확인 후 보완]`

## 3. 가장 먼저 개선할 문제

선택:
- **작은 이물의 FN (Pattern 1)**

선택 이유:
- 조각김치 이물검출에서는 실제 이물을 놓치는 FN이 가장 위험합니다.
- FN 63개가 Validation 전체에서 반복되고, 크기가 작을수록 뚜렷하게 늘어납니다.
- Pattern 2(Class 5)도 대부분 작은 객체라 같은 실험으로 일부 확인할 수 있습니다.

## 4. 원인 가설

원본 사진(긴 변 4848px)을 640으로 줄이면 30px 이물이 약 4px이 되어,
입력 Image Size가 작은 이물의 특징을 충분히 표현하지 못해 FN이 발생했을 가능성이 있다고 가정합니다.

이렇게 판단한 이유:
- 크기가 작을수록 놓친 비율이 커짐 (36% → 22% → 5%)
- 찾은 박스의 위치는 정확함 (TP IoU 중앙값 0.92) → 박스 회귀보다 검출 자체의 문제
- 학습량 부족은 아닐 가능성이 큼: 예비 실험 A(100 epoch)도 best가 70~75 epoch였음

## 5. 다음 개선 실험

Baseline:
- imgsz = 640

Improved Experiment:
- **imgsz = 960** (960이면 30px 이물이 약 6px)

유지할 조건:
- 같은 Dataset Version (kimchi_v1)
- 같은 Train 600 / Validation 75
- 같은 Model 계열 (YOLO11n)
- 같은 batch 8 · epochs 70 · patience 30 · seed 42
- 같은 평가 방법 (conf 0.25 · IoU 0.5 · 같은 09·10 스크립트)

변경 변수:
- Image Size 하나만 변경

바꾸지 않는 것:
- epochs 증가: A에서 100 epoch 효과 없음 확인
- batch 변경: 정확도보다 학습 안정성·속도에 영향, 960에서는 메모리 확인 필요

확인할 결과:
- Validation Recall 변화 (07 공식 Recall · 09 매칭 Recall TP/정답 0.695 둘 다)
- 크기별 놓친 비율, 특히 small 36%의 변화 (`10_fn_by_size.py`)
- Class별 Recall, 특히 leaf_paper · disease_browning
- Precision 변화와 IoU 0 FP 수
- mAP50 / mAP50-95 변화
- 대표 실패 이미지 18장 전후 비교

## 6. 한계

- Validation 75장 → mAP 0.01~0.02 차이는 잡음일 수 있음. Class별 Recall · 크기별 놓친 수로 함께 판단
- Validation에 Class 6(green_onion_pepper) 없음
- T17_V 15장은 Train의 T17과 같은 촬영 묶음 → Val 점수가 실제보다 좋게 나올 수 있음
- eval_exclude 4장(pHash 중복)은 이번 숫자에 포함됨 → 제외 시 재계산 필요
