# Final Model Selection

> 교과 8 · ⑤ Experiment · 2026-10-19 · 작성: 박하솔 · 결정: 팀 결정 (2026-10-19)
> **선택 시점: Frozen Test를 보기 전** — Test 결과를 보고 모델을 바꾸지 않는다

## 한 줄 요약

| 항목 | 내용 |
|---|---|
| Final | **EXP003 — yolo11n · imgsz 1280** (`runs/exp003/weights/best.pt`, 37에포크) |
| 이유 | Baseline 대비 단일 변수 실험 중 P · R · mAP50 · mAP50-95 모두 1등 · 정밀도 0.948 · 계산량 약 26 GFLOPs |
| 제외 | EXP004 (s · 1280, mAP50-95 0.490) — Baseline 대비 2변수 누적 · 정밀도 하락 · 계산량 3.3배 → 교과 14 참고 |
| Test | `models/final/final_best.pt` · **imgsz=1280** · 1회 → **mAP50-95 0.4115 · Recall 0.466** (Val 0.4457 · 0.491) |

---

## ① 선택한 모델

| 항목 | 값 |
|---|---|
| Final Model | **EXP003 — yolo11n · imgsz 1280** |
| 원본 Weight | `runs/exp003/weights/best.pt` (37에포크, 조기 종료 67에포크) |
| 보관 위치 | `models/improved/exp003_best.pt` → `models/final/final_best.pt` |
| Dataset | `manifests/train.csv` md5 fa803448 · `val.csv` md5 e1c68baa (`DATASET_VERSION = kimchi_v4`) |
| Frozen Test 실행 조건 | **imgsz=1280**, split=test, 한 번만 — `python scripts/13_evaluate_final_test.py` |
| Frozen Test 결과 | `reports/final_metrics.csv` · `final_class_metrics.csv` · `figures/final_test_confusion_matrix.png` |

---

## ② 같은 Validation에서의 비교

| 모델 | 변경 (Baseline 대비) | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| Baseline | — | 0.9161 | 0.4437 | 0.5060 | 0.3445 |
| EXP001 | imgsz 960 (1개) | 0.8795 | 0.4844 | 0.5293 | 0.4231 |
| EXP002 | yolo11s (1개) | 0.9408 | 0.4768 | 0.5442 | 0.4148 |
| **EXP003** | **imgsz 1280 (1개)** | **0.9477** | **0.4914** | **0.5498** | **0.4457** |
| EXP004 (참고) | imgsz 1280 + yolo11s (2개, 누적) | 0.7448 | 0.5453 | 0.5828 | 0.4900 |

---

## ③ 선택 이유

1. **규칙에 맞는 비교에서 1등** — Final 후보는 Baseline 대비 단일 변수 실험(EXP001~003) 중에서 고른다 (가이드 20.2 · `improvement_experiment.md` ⑪). 그중 EXP003이 Precision · Recall · mAP50 · mAP50-95 네 지표 모두 1등이고, EXP001 대비 mAP50-95 +0.023으로 채택 기준(+0.02)을 넘는다. 10/16 계획(Part 1 ⑤)의 판단 묶음(재현율 ↑ · mAP 유지 이상 · 정밀도 유지)도 모두 충족한다.
2. **가설을 직접 증명한 실험** — 640 → 960 → 1280으로 해상도만 키울수록 점수가 계속 올라, 실패 분석의 "작은 이물 해상도 부족" 가설과 원인이 한 변수로 연결된다.
3. **정밀도가 가장 높다** — 0.948 (Class 6 제외 0.937). 8일차 Auto Label에서 Final 모델이 후보 라벨을 만들 때 잘못 잡은 박스가 적어 사람 검수 부담이 줄어든다.
4. **계산량** — 약 26 GFLOPs로 EXP004(약 86)의 1/3. 교과 14 컨베이어 실시간 검사로 넘어갈 모델이라 속도도 기준에 넣었다.

---

## ④ EXP004를 Final로 고르지 않은 이유

- 점수만 보면 EXP004가 더 높다 (mAP50-95 0.490, EXP003 대비 +0.044, 재현율 +0.054). 이 점은 인정하고 기록한다.
- 그러나 Baseline 대비 두 변수(모델 + 해상도)가 바뀐 누적 실험이라 Final 후보 범위 밖이다.
- 정밀도가 0.745로 내려갔다 (대부분 Val 1개뿐인 파·고추 영향, Class 6 제외 시 0.894).
- 계산량이 약 3.3배다.
- Val 66장 · seed 1개로 잰 차이라 재실행 시 줄어들 수 있다.
- 병해·갈변 재현율은 EXP004도 0이다 — 무거운 모델로도 핵심 데이터 문제는 해결되지 않았다.
- → **교과 14에서 속도 여유가 있으면 다음 후보**로 handoff에 기록한다.

---

## ⑤ 대표 FP / FN 변화 (Baseline → EXP003)

- 같은 판정 기준(④ Evaluation `src/failure_analyzer.py` · conf ≥ 0.25 · IoU ≥ 0.5)으로 Baseline과 EXP001~004를 Val 66장에서 다시 셌다.
  - 실패 유형 개수(TP · FP · FN · CLASS · BBOX): `reports/failure_compare.csv`
  - 크기별 놓친 비율(small · medium · large, Class별): `reports/fn_by_size_compare.csv`
  - 실행: `python scripts/11c_compare_failures.py` (예측 TXT만 저장, 사진 저장 없음)

| 모델 | TP | FP | FN | CLASS | BBOX | small 놓침 |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 157 | 24 | 82 | 11 | 6 | 63.9% |
| **EXP003** | **164** | **21** | **78** | **8** | **6** | **60.2%** |
| 변화 | +7 | -3 | -4 | -3 | 0 | -3.7%p |

- **FN:** 82 → 78, 작은 이물 놓친 비율 63.9% → 60.2% → 실패 분석에서 고르려던 문제가 같은 방향으로 줄었다.
- **FP · CLASS:** 헛박스 -3, Class 혼동 -3 → 단일 변수 실험 중 FP가 가장 적다 (EXP001 30 · EXP002 25 · EXP003 21).
- **남은 문제:** 작은 이물은 여전히 60%를 놓친다. EXP004(49.4%)처럼 모델까지 키우면 더 줄지만 정밀도 · 계산량 문제가 있다 (④).
- Class별 지표: 4개 Class(나뭇잎 · 플라스틱 · 나뭇가지 · 벌레) mAP50-95가 EXP001 · EXP002보다 모두 높다.
- 병해·파고추를 뺀 나머지 4개 Class 평균 재현율: EXP001 0.727 · EXP002 0.715 · EXP003 0.737.
- 혼동 행렬: `reports/figures/exp003_confusion_matrix.png`

---

## ⑥ 한계

- 실패 분석의 "작은 이물 FN" 가설은 해상도를 올릴수록 점수가 단계적으로 오른 것으로 확인했다. 다만 작은 이물 놓친 비율은 63.9% → 60.2%로 줄어든 폭이 작다 (`reports/fn_by_size_compare.csv`).
- 병해·갈변 재현율 0 (Train 쏠림), 파·고추 N/A (Val 1개) — 해상도 · 모델로 해결되지 않았다. 교과 11 컨베이어에서 새로 찍은 데이터로 보완한다.
- EXP001 대비 차이(+0.023)는 기준을 크게 넘지 않는다. 다만 640 → 960 → 1280으로 4개 Class가 같은 방향으로 올랐다.
- 교과 14 속도 대안: 더 빠른 쪽은 EXP001 (n · 960, 약 15 GFLOPs), 더 정확한 쪽은 EXP004 (s · 1280, 약 86 GFLOPs).
- 검출 conf 조정은 Validation으로만 정하고 Test 전에 고정한다.

---

## ⑦ Frozen Test 운영 규칙

- Final(EXP003)은 위 Validation 근거로 **Test를 열기 전에** 확정했다.
- Test는 `scripts/13_evaluate_final_test.py`로 **한 번만** 실행한다 (결과 파일이 있으면 스크립트가 멈춘다).
- Test 점수가 Validation보다 낮게 나와도 모델이나 설정을 바꾸지 않고 그대로 기록한다.
- Test에도 파·고추는 1개뿐이라 Class 6 점수는 참고만 한다.

---

### 75장 / 74장 (eval_exclude 제외)

| 기준 | Precision | Recall | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|
| 75장 (전체 · 객체 428) | 0.6046 | 0.4660 | 0.4934 | 0.4115 |
| 74장 (eval_exclude 제외 · 객체 421) | 0.6047 | 0.4655 | 0.4992 | 0.4171 |

- `250411_140406550160.jpg`(T08)는 검수 단계에서 Class가 모호한 사진(갈변/이물 판단 애매)으로 확인되어, Split 확정 시점(10/15, Test 평가 전)에 `eval_exclude=True`로 지정했다 (`docs/split_policy.md`).
- 13번 스크립트는 test 폴더 75장 전체로 평가했으므로, 75장 결과는 그대로 두고 같은 모델 · 같은 설정으로 74장 결과를 추가 기록했다 (`scripts/13b_evaluate_final_test_eval74.py`).
- 모델 · imgsz · conf는 바꾸지 않았다. 제외 후 mAP50-95는 0.4115 → 0.4171로 결론에 변화 없다.
- 실행 속도 (참고): RTX 3060 · imgsz 1280 · 사진 1장당 추론 8.7ms (전처리 · 후처리 포함 약 15ms).

### Class별 (Test)

| Class | 객체 | P | R | mAP50 | mAP50-95 | Val mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|
| leaf_paper | 14 | 0.320 | 0.857 | 0.667 | 0.581 | 0.688 |
| plastic_stone_metal | 181 | 0.977 | 0.480 | 0.783 | 0.633 | 0.604 |
| branch | 177 | 0.990 | 0.559 | 0.953 | 0.806 | 0.602 |
| insect | 10 | 0.341 | 0.900 | 0.495 | 0.419 | 0.778 |
| disease_browning | 45 | 1.000 | 0.000 | 0.063 | 0.029 | 0.003 |
| green_onion_pepper | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### 해석

- **mAP50-95 · Recall은 Validation과 비슷하다** (-0.034 · -0.025). Validation에서 고른 모델이 처음 보는 Test에서도 비슷한 수준을 유지했다.
- **객체가 많은 Class는 오히려 좋아졌다:** branch 0.602 → 0.806, plastic 0.604 → 0.633 (Test 객체의 84%).
- **Precision 하락(0.948 → 0.605)의 이유**
  - 파·고추: Test에 1개뿐인데 헛박스가 생겨 P 1.0 → 0.0 → 6개 Class 평균에서 약 -0.17
  - leaf_paper(14개) · insect(10개): 대부분 찾지만(R 0.86 · 0.90) 헛박스가 많아 P 0.32 · 0.34
  - branch · plastic은 P 0.98 이상 유지 → 객체가 적은 Class에서 헛박스가 많다
- **병해·갈변:** Test에서도 Recall 0 (45개) → Validation에서 기록한 한계와 같다.
- **규칙:** Test 결과를 보고 모델 · conf · 설정을 바꾸지 않았다. 헛박스는 교과 14에서 Validation으로 conf 기준을 정할 때 다시 본다.

