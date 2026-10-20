# Kimchi Foreign Object Detection — YOLO11

## 1. 프로젝트 목적

### 개요

조각김치 이물검출 객체검출 · 2조 프로젝트입니다. 교과 7 에서 전수 검수한 **FINAL 900쌍**으로 YOLO11 을 학습하고, **실패 분석 → 한 변수 개선 → Final Model → Frozen Test → Auto Label** 까지 완성합니다.

목표는 높은 점수가 아니라 **신뢰할 수 있는 데이터**입니다. 같은 촬영 묶음이 학습과 평가에 섞이지 않게 Split 을 다시 만들고, 실험은 변수 하나씩 바꾸고, Final Model 은 **Frozen Test 를 보기 전에** 확정했습니다.

<br>

### 작업 결과

Baseline 은 작은 이물을 **63.9%** 놓쳤습니다. "640 으로 줄이면 작은 이물이 사라진다" 는 가설로 이미지 크기만 키운 결과 점수가 단계적으로 올라, **EXP003 (yolo11n · 1280)** 을 Final Model 로 선택했습니다.

| 핵심 지표 | 결과 |
|---|---|
| 데이터 | FINAL **900쌍** → Train 609 · Val 66 · Test 75 · Bridge 150 |
| Baseline | yolo11n · 640 · Val mAP50-95 **0.345** |
| Final Model | **EXP003** yolo11n · 1280 · Val mAP50-95 **0.446 (+29%)** |
| Frozen Test | 1회 · mAP50-95 **0.4115** (75장) · **0.4171** (74장) |
| 속도 | 약 26 GFLOPs · RTX 3060 사진 1장당 추론 **8.7ms** |

근거 → [Final Model Selection](reports/final_model_selection.md) · [Baseline vs Improved](reports/baseline_vs_improved.md)

<br>

### Architecture

<!-- TODO: Architecture 그림 · 설명 -->

<br>

### 팀원 소개

| 직책 | 역할 | 브랜치 | 주요 산출물 |
|---|---|---|---|
| PM | 일정 · GitHub 관리 · 발표 총괄 | feature/pm | README · 발표 · Acceptance Test |
| Data | Dataset Audit · Split · 누수 점검 | feature/dataset-audit | Split v4-B · manifests |
| Training | Smoke Test · Baseline 학습 | feature/train | Baseline Model |
| Evaluation | 평가 모듈 · 실패 분석 · Frozen Test | feature/evaluation | Failure Analysis · Final Test |
| Experiment | 한 변수 개선 실험 · Final 선택 | feature/experiment | EXP001 ~ 004 · Final Model |
| Inference | Detection · Auto Label · Human Review | feature/inference | candidate · reviewed labels |

<br>

### 산출물

| 번호 | 산출물 | 위치 | 상태 |
|---:|---|---|---|
| 1 | Dataset Version | `configs/` · `manifests/` · [split_policy](docs/split_policy.md) | 완료 · kimchi_v4 |
| 2 | Baseline Model | `models/baseline/` · [baseline_metrics](reports/baseline_metrics.csv) | 완료 |
| 3 | Failure Analysis | [failure_analysis](reports/failure_analysis.csv) · `demo/failure_analysis/` | 완료 |
| 4 | Improved / Final Model | `models/improved/` · `models/final/` · [selection](reports/final_model_selection.md) | 완료 · EXP003 |
| 5 | 성능 · 실험 기록 | [experiment_log](reports/experiment_log.csv) · [final_metrics](reports/final_metrics.csv) · [figures](reports/figures) | 완료 |
| 6 | Detection · Auto Label | `demo/prediction_images/` · `demo/auto_label/` | 진행 중 |
| 7 | 문서 · 교과 14 연결 | README · `reports/acceptance_test.md` · `docs/handoff_subject14.md` | 진행 중 |
| 8 | 발표 · 시연 | `presentation/` · `demo/*.mp4` | 진행 중 |

<br>

### 바로가기

| 용도 | 바로가기 |
|---|---|
| 처음 실행 | [5. 실행방법](#5-실행방법) |
| 성과 · 근거 | [11. Improvement](#11-improvement) · [12. Final Test](#12-final-test) |
| 한계 · 다음 단계 | [14. 알려진 한계](#14-알려진-한계) · [15. 교과 14 Handoff](#15-교과-14-handoff) |

<br><br>

## 2. 데이터 설명

- 입력: 교과 7 **FINAL 900쌍** (JPG 900 · YOLO TXT 900 · BBox 4,405) → [교과 8 Handoff](../project7/docs/10_subject08_handoff.md)
- 원본: 4848 × 2704 · AI캠퍼스 교육용 **100% 가상 생성** · **NDA 대상**
- 장면: 김치 + 이물 725 · 이물만 149 · 정상 김치 24 · 이물 없음 2
- Dataset Version: **kimchi_v4**

| 위치 | 내용 | Git |
|---|---|---|
| `data/final/` | 교과 7 FINAL 900쌍 · 메일 · USB 로 받음 | 제외 |
| `data/yolo/` | train · val · test (03_build_split 생성) | 제외 |
| `data/bridge_holdout/` | 교과 14 용 150장 · 학습 · 평가 미사용 | 제외 |

<br><br>

## 3. Class

교과 7 번호 그대로 · **번호 변경 금지** · 설정 [configs/dataset.yaml](configs/dataset.yaml)

| Class | 이름 | Train | Val | Test |
|---:|---|---:|---:|---:|
| 0 | 나뭇잎 · 종이류 | 489 | 27 | 14 |
| 1 | 플라스틱 · 돌 · 금속 | 1,019 | 145 | 181 |
| 2 | 나뭇가지류 | 673 | 39 | 177 |
| 3 | 벌레류 | 323 | 23 | 10 |
| 4 | 고무장갑 — 사용 안 함 · 배경 | 0 | 0 | 0 |
| 5 | 병해 · 갈변 | 163 | 21 | 45 |
| 6 | 파 · 고추 | 249 | 1 | 1 |

- **김치 · 고무장갑 = 배경** · 파 · 고추는 Val · Test 1개씩이라 **평가 불가 · 참고만**

<br><br>

## 4. 환경

| 항목 | 값 |
|---|---|
| OS | Windows 11 + WSL2 Ubuntu + VS Code |
| GPU | NVIDIA GeForce RTX 3060 12GB (팀 PC 동일) |
| Python · PyTorch | 3.14.4 · 2.14.1 + cu130 |
| Ultralytics | 8.4.175 |
| 공통 설정 | [src/project_config.py](src/project_config.py) — 경로 · Class · Baseline 조건 · conf 0.25 · IoU 0.5 |

<br><br>

## 5. 실행방법

### 설치 · 데이터

WSL · Git 설치는 [교과 7 빠른 시작](../project7/README.md#빠른-시작) 과 같습니다.

```bash
git clone https://github.com/sunghyunglee6334-web/group2-project.git ~/group2_project
cd ~/group2_project/project8
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
```

메일 · USB 로 받은 FINAL 을 `data/final/` (images · labels · manifest_final.csv) 에 넣고 Split 을 만듭니다.

```bash
python scripts/01_check_environment.py     # CUDA available: True
python scripts/03_build_split_v4.py        # data/yolo · configs/dataset.yaml 생성
```

Weight 6개(`models/`)는 Git 으로 받아지므로 **다시 학습하지 않아도** 평가 · Detection 을 바로 실행할 수 있습니다.

<br>

### 실행 순서

| 단계 | 스크립트 |
|---|---|
| Split · 점검 | `02_audit` → `03_build_split_v4` → `03b_check_phash` → `04_preview_dataset` |
| Smoke · Baseline | `05_smoke_train` → `06_train_baseline` → `07_evaluate_baseline` |
| 실패 분석 | `compare_gt_pred` → `09_collect_failures` → `10_fn_by_size` → `12_failure_deliverables` |
| 개선 실험 | `11_train_experiment` → `11b_evaluate_experiment` → `11c_compare_failures` |
| Frozen Test | `13_evaluate_final_test` (**1회 · 완료**) · `13b_evaluate_final_test_eval74` |
| 자동 테스트 | `pytest tests/` |

<br>

### 폴더 구조

```text
project8/
├── configs/       ← 데이터 설정
├── src/           ← 공통 코드
├── scripts/       ← 실행 01 ~ 13
├── tests/         ← 테스트
├── manifests/     ← Split 목록
├── models/        ← Weight
├── reports/       ← 결과 · 문서
├── docs/          ← 기준 · 기록
├── runs/          ← 학습 기록
├── demo/          ← 시연 결과
└── data/          ← 데이터 · Git 제외
```

<br>

### 주의사항

- **원본 사진 · 결과 이미지 · 영상은 Git 금지** · TXT · CSV · 문서 · 그래프는 허용 (10/13 강사님 확인)
- `models/` Weight 는 팀 공유 (10/20) · `runs/` Weight 는 제외
- **Frozen Test 는 한 번만** · **Bridge Holdout 은 교과 8 에서 사용 금지**
- main 은 PR 로만 · `git add .` · `-f` 금지

<br><br>

## 6. Dataset Split

**v4-B (10/19 · PR #61)** · 기준 [split_policy](docs/split_policy.md) · 결과 [split_report](reports/split_report.md)

| 역할 | 장수 | 촬영 묶음 | 쓰는 곳 |
|---|---:|---|---|
| Train | 609 | 10개 묶음 | 학습 |
| Validation | 66 | T01 · T03 · T07 | 모델 비교 · Final 선택 |
| Frozen Test | 75 | T08 · T14 | Final 확정 후 **1회** |
| Bridge Holdout | 150 | T09 · T11 · T16 | 교과 14 · 봉인 |

- **5분 촬영 묶음 단위**로 통째 배정 — 같은 이물을 옮겨 가며 찍어서, 사진 단위로 나누면 누수
- **누수 확인** — 사진 단위 Recall **0.781** → 묶음 단위 **0.444** · 부풀린 점수를 걷어내고 전부 재학습
- **eval_exclude** — 라벨이 애매한 Test 1장 (`250411_140406550160.jpg`) 은 평가 제외 대상

<br><br>

## 7. Smoke Test

본 학습 전에 학습 → 저장 → 예측이 끝까지 도는지, GPU 메모리를 확인했습니다 (성능 판단용 아님).

| 실행 | 조건 | GPU 최대 |
|---|---|---:|
| smoke_v1 | 960 · batch 16 · 3 epoch | 4.86 GB |
| smoke_v2 | 1280 · batch 16 · 3 epoch | 9.02 GB |

- 결정: **batch 8** 이면 1280 까지 같은 조건으로 비교 가능 → [smoke_test](reports/smoke_test.md)

<br><br>

## 8. Baseline

| 항목 | 값 | 이유 |
|---|---|---|
| Model | yolo11n | 가장 가벼운 기준 모델 |
| imgsz · batch | 640 · 8 | 1280 까지 같은 batch 비교 |
| epochs · patience | 70 · 30 | 예비 학습 best 70 ~ 75 |
| seed | 42 | 재현 |

- 학습 7.9분 · best epoch 50 · Train 609 만 학습 · Test · Bridge 미사용
- [학습 조건](reports/baseline_training_condition.md) · `models/baseline/baseline_best.pt`

<br><br>

## 9. 평가

모든 모델을 같은 모듈 [evaluate_detector.py](src/evaluate_detector.py) 로 평가합니다. **대표 지표는 mAP50-95** (박스를 얼마나 정확히 그렸는지까지 봄).

| Baseline (Val 66) | Precision | Recall | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|
| 결과 | 0.917 | 0.444 | 0.506 | **0.345** |

- 잡은 건 대부분 맞지만 이물 10개 중 약 6개를 놓침
- `allow_test=True` 없이는 Test 평가를 막음 · [Class별](reports/baseline_class_metrics.csv) · [figures](reports/figures)

<br><br>

## 10. Failure Analysis

conf ≥ 0.25 · IoU ≥ 0.5 기준 박스 판정 · [failure_compare](reports/failure_compare.csv) · [fn_by_size_compare](reports/fn_by_size_compare.csv)

| FN 놓침 | FP 헛박스 | CLASS 혼동 | BBOX 어긋남 | 작은 이물 놓침 |
|---:|---:|---:|---:|---:|
| **82** | 24 | 11 | 6 | **63.9%** |

- **작은 이물 FN** — 640 축소 시 30px → 약 4px → **해상도 가설**
- **Class 혼동** — 나뭇가지 ↔ 플라스틱 ↔ 나뭇잎 → 모델 용량 가설
- **병해 · 갈변 Recall 0** — 데이터가 Bridge 묶음에 몰림 → 데이터 문제
- 대표 사례 → [failure_analysis.csv](reports/failure_analysis.csv) · 가설 원문 [failure_hypothesis](reports/failure_hypothesis.md) (Split v1 기준)

<br><br>

## 11. Improvement

**Baseline 에서 변수 하나만** · 채택 기준 **mAP50-95 +0.02 를 결과 보기 전(10/16)에 결정**

| 실험 | 바꾼 것 | Precision | Recall | mAP50-95 | 판정 |
|---|---|---:|---:|---:|---|
| Baseline | — | 0.916 | 0.444 | 0.345 | 기준 |
| EXP001 | imgsz 960 | 0.880 | 0.484 | 0.423 | EXP003 으로 대체 |
| EXP002 | yolo11s | 0.941 | 0.477 | 0.415 | REJECT |
| **EXP003** | **imgsz 1280** | **0.948** | **0.491** | **0.446** | **FINAL** |
| EXP004 | 1280 + s | 0.745 | 0.545 | 0.490 | 참고 (변수 2개) |

- 640 → 960 → 1280 으로 단계적 상승 → 해상도 가설 확인 · EXP003 을 **Test 전에** Final 로 확정
- EXP004 는 더 높지만 계산량 **3.3배** · 실시간 속도 미확인 · 변수 2개 → 교과 14 후보
- [experiment_log](reports/experiment_log.csv) · [improvement_experiment](reports/improvement_experiment.md) · [baseline_vs_improved](reports/baseline_vs_improved.md)

<br><br>

## 12. Final Test

Final Model 을 처음 보는 Test 에 **한 번만** 평가 · 결과를 보고 모델을 바꾸지 않음

| 기준 | Precision | Recall | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|
| Validation 66장 | 0.948 | 0.491 | 0.550 | 0.446 |
| **Frozen Test 75장** | **0.605** | **0.466** | **0.493** | **0.4115** |
| Frozen Test 74장 | 0.605 | 0.466 | 0.499 | 0.4171 |

- mAP50-95 · Recall 은 Validation 과 비슷하게 유지 · 나뭇가지는 0.602 → **0.806** 상승
- Precision 하락 — 파 · 고추(Test 1개) 헛박스 · 나뭇잎 · 벌레 헛박스 (P 0.32 · 0.34)
- 74장 — 애매한 1장은 Test 전에 제외로 정했으나 75장으로 평가되어, 74장 결과를 추가 기록 (결론 같음)
- [final_metrics](reports/final_metrics.csv) · [eval74](reports/final_metrics_eval74.csv) · [혼동 행렬](reports/figures/final_test_confusion_matrix.png)

<br><br>

## 13. Auto Label

Final Model 이 만든 **후보 TXT** 를 사람이 **교과 7 라벨링 프로그램**에서 확인 · 수정해 확정합니다.

```text
새 사진 → Final Model (1280 · conf 0.25) → 후보 TXT → 교과 7 프로그램 → Human Review → 확정 TXT
```

| 산출물 | 위치 | 상태 |
|---|---|---|
| Detection 결과 | `demo/prediction_images/` | 진행 중 |
| 후보 · 검수 라벨 | `demo/auto_label/candidate_labels/` · `reviewed_labels/` | 진행 중 |
| 검수 통계 | `reports/auto_label_review.csv` | 진행 중 |

- 교과 7 프로그램에 Detection · Auto Label 버튼 추가 (PR #71)
- 검수 결과: <!-- TODO: 이미지 수 · 후보 BBox · 승인 · 수정 · 삭제 · 추가 -->

<br><br>

## 14. 알려진 한계

| 한계 | 원인 | 다음 |
|---|---|---|
| 병해 · 갈변 Recall 0 | 46% 가 Bridge 묶음 · Train 35% | 교과 11 새 촬영 |
| 파 · 고추 평가 불가 | 251 중 249 가 한 묶음 | 교과 11 컨베이어 |
| 소수 Class 헛박스 | 나뭇잎 · 벌레 P 0.32 · 0.34 | 교과 14 현장 확인 |
| 작은 이물 60% 놓침 | 해상도만으로는 개선 폭 작음 | EXP004 (49.4%) 참고 |
| 1280 계산량 | Baseline 의 약 4배 | Jetson 속도 · EXP001 대안 |
| Val 66 · seed 1개 | 시간 제약 | 작은 차이는 신뢰 낮음 |

<br><br>

## 15. 교과 14 Handoff

<!-- TODO: docs/handoff_subject14.md 연결 -->

| 넘기는 것 | 내용 |
|---|---|
| Final Model | `models/final/final_best.pt` · EXP003 · imgsz 1280 · conf 0.25 |
| Dataset | kimchi_v4 · Split v4-B · `manifests/` |
| Bridge Holdout | 150장 · T09 · T11 · T16 · 교과 8 미사용 |
| Frozen Test | mAP50-95 0.4115 (74장 0.4171) |
| 다음 후보 | 더 정확: EXP004 (약 86 GFLOPs) · 더 빠름: EXP001 (약 15 GFLOPs) |
| 한계 | [14. 알려진 한계](#14-알려진-한계) |
