# 개선 실험 계획 · EXP001 (imgsz 640 → 960)
   > ⚠ **Part 1 (①~⑧)은 옛 Split(v1 · Val 75) 기준**으로 10/16에 작성한 계획 원문이다. 실행 결과는 Part 2(Val 66) 기준.
   >
   
> **문서 구성**
> - **Part 1 (①~⑧):** 10/16 학습 전에 작성한 EXP001 계획 원문 (실패 분석 → 가설 → 조건 → 판단 기준)
> - **Part 2 (⑨~⑬):** 10/19 실험 실행 — EXP001~004 조건 · 판정 기준 · 결과 · 한계
> - 실행 스크립트: `scripts/11_train_experiment.py` · 평가 `11b_evaluate_experiment.py` · 실패 비교 `11c_compare_failures.py`


> 교과 8 · ⑤ Experiment · 2026-10-16 · 작성: 박하솔
> 상태: **계획 (학습 전 작성)** · 비교 기준: baseline_v1 · dataset kimchi_v1 · split = Validation (75장 / 객체 318개)
> 근거 자료: ④ Evaluation의 Baseline 상세 결과 · 평가와 실패분석 · IoU 분석 (2026-10-16)

---

## ① 한 줄 요약

| 항목 | 내용 |
|---|---|
| 관찰 | 작은 이물일수록 많이 놓친다 (small FN 36% → large 5%) |
| 가설 | 640 입력에서는 작은 이물이 너무 작게 줄어들어 특징이 사라진다 |
| 바꿀 변수 | **imgsz 640 → 960 (딱 하나)** |
| 목표 | Recall 상승 · small FN 감소, Precision은 크게 떨어지지 않게 |
| 실험 ID | EXP001 · run 이름 `exp001` · Weight `models/improved/exp001_best.pt` |

---

## ② Baseline 현재 상태 (출발점)

| Precision | Recall | mAP50 | mAP50-95 |
|---:|---:|---:|---:|
| 0.890 | **0.592** | 0.658 | 0.505 |

- 잡은 것 대부분은 맞지만(P 0.89), 실제 이물의 약 40%를 놓친다(R 0.59).
- 학습 곡선상 Recall은 30 epoch 이후 0.55~0.60에서 멈춤 → **epoch를 늘려도 안 오를 가능성이 큼.** 학습량이 아니라 입력 조건을 바꿔야 한다.

### 박스 판정 결과 (conf 0.25 · IoU 0.5 기준)

| 유형 | 개수 | 의미 |
|---|---:|---|
| TP | 221 | 맞힘 (IoU 중앙값 0.920 → 박스 위치는 정확) |
| **FN** | **63** | **있는데 못 찾음 ← 가장 큰 문제** |
| FP | 93 | 없는데 찾음 (86%가 IoU 0, 김치 조각을 이물로 착각한 것으로 추정) |
| CLASS | 17 | 위치는 맞고 Class 틀림 |
| BBOX | 17 | Class는 맞고 박스가 어긋남 (모두 IoU 0.1~0.5, 작은 이물) |

---

## ③ 왜 imgsz인가 (실패분석 → 가설)

### 크기별 놓친 비율 (FN ÷ 정답 객체)

크기 = 긴 변 640px 기준, Class마다 1/3씩 나눈 Split 기준.

| Class | small | medium | large |
|---|---:|---:|---:|
| leaf_paper | **80% (8/10)** | 0% (0/3) | 0% (0/16) |
| plastic_stone_metal | 23% (3/13) | 15% (4/27) | 0% (0/20) |
| branch | 26% (18/69) | 24% (13/55) | 7% (6/81) |
| insect | 0% (0/2) | 0% (0/3) | 0% (0/5) |
| disease_browning | **89% (8/9)** | 100% (3/3) | 0% (0/2) |
| **전체** | **36% (37/103)** | **22% (20/91)** | **5% (6/124)** |

### 연결 고리

```
4K 원본 → 640으로 축소하면 작은 이물은 몇 픽셀만 남음
        ↓
모델이 볼 특징이 부족 → small에서 FN 36%
        ↓
imgsz 960 → 같은 이물이 1.5배 크게 들어감
        ↓
small FN 감소 → Recall 상승 기대
```

- 찾은 박스는 IoU 0.9 이상이 62% → **박스 그리는 능력은 충분**, 문제는 "못 보는 것"
- BBOX 오류 17개도 전부 작은 이물 → 해상도가 오르면 IoU 0.3~0.5 박스가 0.5 이상으로 올라올 수 있음
- Evaluation 결론과 같은 방향: "Improved imgsz 640 → 960으로 바꾸는 근거"

### 이번 실험으로 해결 안 될 것 (미리 기록)

- **Class 5 disease_browning (Recall 0.000):** 14개 중 10개가 background로 처리. 크기보다 **갈변과 김치의 색 구분 문제**로 보임 → imgsz로는 개선 가능성 낮음. 결과가 안 좋아도 그대로 기록.
- **FP 93개:** 해상도를 올리면 김치 결·고춧가루 같은 디테일도 커져서 오히려 늘 수 있음 → 감시 지표로 둠.

---

## ④ 실험 조건 (바꾸는 것 1개 · 나머지 고정)

| 항목 | Baseline (baseline_v1) | EXP001 | 변경 |
|---|---|---|:-:|
| Model | yolo11n.pt (사전학습) | yolo11n.pt (사전학습) | - |
| **imgsz** | **640** | **960** | **변경** |
| batch | 8 | 8 | - |
| epochs | 70 | 70 | - |
| patience | 30 | 30 | - |
| seed | 42 | 42 | - |
| optimizer / lr0 | auto / 0.01 | auto / 0.01 | - |
| Dataset Version | kimchi_v1 | kimchi_v1 | - |
| Train manifest | train.csv rows=600 md5=0328cbb2 | 같은 파일 | - |
| Val manifest | val.csv rows=75 md5=59a179dc | 같은 파일 | - |
| 판정 기준 | conf 0.25 · IoU 0.5 | conf 0.25 · IoU 0.5 | - |
| GPU | RTX 3060 12GB | RTX 3060 12GB | - |

### batch를 그대로 두는 이유

- imgsz를 키우면 GPU 메모리가 늘어서 보통 batch를 줄이는데, 그러면 변수가 2개가 됨.
- Smoke Test에서 **imgsz 960 + batch 16**으로 최대 4.86GB / 12GB 사용 확인 (`reports/smoke_gpu_memory.json`) → batch 8이면 여유 충분. **batch 8 유지.**

### 학습 전 확인

- [ ] `train.csv`, `val.csv` md5가 위 값과 같은지
- [ ] `configs/dataset.yaml` 변경 없음
- [ ] Test · Bridge Holdout 미사용 (`test_bridge_used: false`)
- [ ] 예상 학습 시간: Baseline 7.7분 → 960은 연산량 약 2.25배 → **약 15~20분 예상 (추정)**

---

## ⑤ 무엇으로 좋아졌다고 판단하나 (학습 전에 기준 확정)

Val이 75장뿐이라 mAP 0.01~0.02 차이는 잡음일 수 있음 → **숫자 하나가 아니라 아래 묶음으로 판단.**

| 구분 | 지표 | Baseline | 기대 방향 |
|---|---|---:|---|
| 주 지표 | Recall | 0.592 | ↑ |
| 주 지표 | small FN 비율 | 36% (37/103) | ↓ |
| 주 지표 | FN 개수 | 63 | ↓ |
| 보조 | mAP50 / mAP50-95 | 0.658 / 0.505 | 유지 또는 ↑ |
| 보조 | BBOX 오류 (IoU 0.1~0.5) | 17 | ↓ |
| 감시 | Precision | 0.890 | 크게 떨어지지 않기 |
| 감시 | FP 개수 | 93 | 크게 늘지 않기 |
| 기록만 | Class 5 Recall | 0.000 | 변화 기록 |

### 판정 규칙 (제안 · 팀 확인 필요)

| 결과 | 판단 |
|---|---|
| Recall ↑ + small FN ↓ + mAP50 유지 이상 | **EXP001을 Final 후보로** |
| Recall ↑ 했지만 Precision·FP가 크게 악화 | conf 값 조정은 별도 이슈로 기록, Final은 팀 논의 |
| Recall 변화 없음 또는 ↓ | **Baseline 유지**, 가설 기각으로 기록 |

> 실패해도 삭제하지 않는다. "해상도가 원인이 아니었다"는 것도 결과다.

---

## ⑥ 평가 방법 (같은 Validation)

```
models/improved/exp001_best.pt
        ↓
같은 val 75장 (kimchi_v1)
        ↓
Ultralytics val → P · R · mAP50 · mAP50-95 · Class별
        ↓
failure_analyzer (conf 0.25 · IoU 0.5) → TP/FN/FP/CLASS/BBOX · 크기별 FN
        ↓
Baseline 숫자와 표로 비교
```

- 각 모델은 **자기가 학습한 imgsz로 평가** (Baseline 640, EXP001 960). 이게 실제로 쓸 조건이기 때문.
- 크기 구간(small/medium/large)은 **Baseline과 같은 경계값**을 그대로 사용 (EXP001 기준으로 다시 나누지 않음).
- Test 75장은 7일차에 열지 않음. Final 선택 후 8일차에만.

---

## ⑦ 산출물

| 파일 | 내용 | 시점 |
|---|---|---|
| `reports/improvement_experiment.md` | 이 문서 | 학습 전 |
| `scripts/10_train_experiment.py` | `train_detector()` 재사용 학습 스크립트 | 학습 전 |
| `models/improved/exp001_best.pt` | EXP001 best Weight (Git 제외) | 학습 후 |
| `runs/exp001/results.csv` | 학습 로그 | 학습 후 |
| `reports/experiment_log.csv` | 실험 조건 + Val 결과 + 판단 | 평가 후 |
| `reports/figures/exp001_results.png` | 학습 곡선 | 평가 후 |
| `reports/figures/exp001_confusion_matrix.png` | Confusion Matrix | 평가 후 |
| `reports/baseline_vs_improved.md` | 지표 + FP/FN 패턴 비교, Final 후보 결정 | 평가 후 |

---

## ⑧ 확인 필요 · 주의

- **Baseline 조건 표기 불일치:** `reports/baseline_metrics.csv`에는 batch 16 / epochs 100, `reports/baseline_run_info.json`과 Figma 결과에는 batch 8 / epochs 70. 이 문서는 **실제 학습 기록(json) 기준 8 / 70**으로 작성. csv 수정 필요 (④ Evaluation · ③ Train).
- `reports/baseline_training_condition.md` (4일차 산출물) 아직 없음.
- `failure_analyzer.py`가 `feature/evaluation`에만 있음 → ⑥의 크기별 FN 비교는 main 머지 후 가능.
- Val 중 T17_V 15장은 Train과 같은 촬영 묶음 → Val 점수가 실제보다 높게 나올 수 있음. Baseline과 EXP001 모두 같은 조건이라 **비교에는 문제없음**, 절대 성능은 Frozen Test로 판단.


---
---

# Part 2 — 실험 실행 · 결과 (2026-10-19)

## ⑨ 실행 조건

| 항목 | 값 |
|---|---|
| 데이터 | Train 609 · Validation 66 (`manifests/train.csv` md5 fa803448 · `val.csv` md5 e1c68baa) |
| Baseline | yolo11n · imgsz 640 — P 0.9161 · R 0.4437 · mAP50 0.5060 · mAP50-95 0.3445 (`runs/baseline_v1/results.csv` best epoch 50) |
| 고정 조건 | batch 8 · epochs 70 · patience 30 · seed 42 · 증강 기본값 |

- 모든 실험은 Baseline과 같은 manifest(md5)로 학습했다 (`check_same_data_as_baseline()`가 학습 전에 확인).
- 파·고추(Class 6)는 Val에 1개뿐이라 N/A로 두고, Class 6 제외 평균을 함께 본다.

## ⑩ 실험 목록 (기준 대비 변수 1개)

| ID | 기준(base) | 바꾼 변수 | 근거 · 가설 |
|---|---|---|---|
| EXP001 | Baseline | imgsz 640 → **960** | small FN 36% → 640 축소로 작은 이물 특징 손실 (Part 1) |
| EXP002 | Baseline | model yolo11n → **yolo11s** | Class 혼동 17개(박스 IoU 0.9 이상) → 위치는 맞는데 종류 구분 능력 부족 |
| EXP003 | Baseline | imgsz 640 → **1280** | EXP001에서 Baseline 대비 mAP50-95 +0.079 · 재현율 +0.041 → 더 키우면 더 좋아지는지 |
| EXP004 | **EXP003** | model yolo11n → **yolo11s** (1280 유지) | 해상도 · 모델 둘 다 효과가 있어 합치면 더 오르는지 확인 (**누적 실험**) |

- EXP001~003은 Baseline 대비 변수 1개 (Baseline + 1).
- EXP004는 EXP003 대비로는 1개지만 Baseline 대비로는 2개(imgsz + model)가 바뀐 누적 실험이다 → 참고 결과로 기록.
- 실행: `python scripts/11_train_experiment.py --exp exp00N` → 평가 `python scripts/11b_evaluate_experiment.py --exp exp00N` → 실패 비교 `python scripts/11c_compare_failures.py`

## ⑪ 판정 기준

1. Part 1 ⑤의 판단 묶음을 그대로 쓴다: **재현율 ↑ · mAP 유지 이상 · 정밀도 크게 하락하지 않기**.
2. 대표 지표 **mAP50-95가 비교 대상보다 +0.02 이상**이면 KEEP (Val 66장이라 그보다 작은 차이는 잡음으로 본다).
3. **Final 후보는 Baseline 대비 단일 변수 실험(EXP001~003) 중에서** 고른다 (가이드 20.2 · 10/19 팀 결정). 누적 실험(EXP004)은 참고.
4. 비슷하면 재현율 → 추론 계산량 순으로 본다 (교과 14 실시간 검사).

## ⑫ 결과 (Validation 66장)

| 실험 | 변경 | P | R | mAP50 | mAP50-95 | 판정 |
|---|---|---:|---:|---:|---:|---|
| Baseline | n · 640 | 0.9161 | 0.4437 | 0.5060 | 0.3445 | 기준 |
| EXP001 | imgsz 960 | 0.8795 | 0.4844 | 0.5293 | 0.4231 | KEEP → EXP003으로 대체 |
| EXP002 | yolo11s | 0.9408 | 0.4768 | 0.5442 | 0.4148 | REJECT |
| **EXP003** | **imgsz 1280** | **0.9477** | **0.4914** | **0.5498** | **0.4457** | **FINAL** |
| EXP004 | EXP003 + yolo11s | 0.7448 | 0.5453 | 0.5828 | 0.4900 | 참고 (누적 · Final 범위 밖) |

- **해상도 가설 확인:** 같은 n 모델에서 640 → 960 → 1280으로 mAP50-95 0.344 → 0.423 → 0.446, 재현율 0.444 → 0.484 → 0.491로 단계적으로 상승.
- **모델 가설 확인:** 640에서 n → s +0.070, 1280에서 n → s +0.044. 두 해상도 모두 상승.
- **Class 5 병해·갈변:** 모든 실험에서 재현율 0 — Part 1 ③에서 예상한 대로 해상도 · 모델로는 개선되지 않음 (Train 병해 163개 · 35% 쏠림).
- **EXP004 정밀도 0.745:** 하락분 중 약 0.167은 Val 1개뿐인 파·고추 정밀도가 1.0 → 0.0이 된 영향. Class 6 제외 시 0.894.
- 상세: `reports/baseline_vs_improved.md` · 선택 이유: `reports/final_model_selection.md`

## ⑬ 한계 · 확인 필요

- 실패 유형 · 크기별 FN은 `scripts/11c_compare_failures.py`로 Baseline · EXP001~004를 같은 판정 기준(conf 0.25 · IoU 0.5)으로 비교 → `reports/failure_compare.csv` · `reports/fn_by_size_compare.csv`
  - 작은 이물 놓친 비율: Baseline 63.9% → EXP001 57.8% · EXP002 60.2% · EXP003 60.2% · EXP004 49.4%
  - 가설 방향(해상도 ↑ → small FN ↓)은 맞지만 단일 변수에서는 감소 폭이 4~6%p로 작다
- Val 66장 · seed 1개라 EXP001 · EXP003 차이(+0.023)는 크지 않다. 다만 640 → 960 → 1280으로 같은 방향으로 올랐다.
- 병해·갈변은 해상도 · 모델로 개선되지 않았다 → 데이터 보강이 필요하다.
