# Baseline 학습 조건 (baseline_v1) — 산출물 2

* 목적: 개선 실험 전 **비교 기준(Baseline)** 모델을 정하고, 같은 조건으로 다시 만들 수 있게 학습 조건 · 결과를 기록
* 기준 커밋: `d010338` "smoke test, baseline 최종" (2026-10-16 11:45)
* 실행: `python scripts/06_train_baseline.py` → `python scripts/07_evaluate_baseline.py`
* 날짜: 2026-10-16 (학습 11:29:13 → 11:36:58, **7.7분**)

## 1. 학습 조건

| 항목 | 값 | 출처 |
|---|---|---|
| Model | yolo11n.pt (COCO 사전학습) | `BASELINE_CONFIG["model_name"]` |
| Dataset Version | kimchi_v1 | `DATASET_VERSION` |
| Dataset YAML | configs/dataset.yaml (train · val · test, **Bridge 제외**) | 03_build_split 생성 |
| Train Manifest | manifests/train.csv · 600장 · md5 `0328cbb2` | baseline_run_info.json |
| Val Manifest | manifests/val.csv · 75장 · md5 `59a179dc` | baseline_run_info.json |
| Epoch | 70 | `BASELINE_CONFIG` |
| Patience (Early Stopping) | 30 | `BASELINE_CONFIG` |
| Batch | 8 | `BASELINE_CONFIG` |
| Image Size | 640 | `BASELINE_CONFIG` |
| Seed | 42 (deterministic: true) | `BASELINE_CONFIG` |
| Optimizer | auto (Ultralytics 자동 선택) | args.yaml |
| Learning Rate | lr0 0.01 · lrf 0.01 · momentum 0.937 · weight_decay 0.0005 · warmup 3 epoch | args.yaml |
| 증강 | Ultralytics 기본 (mosaic 1.0 · 마지막 10 epoch mosaic 끔 `close_mosaic: 10`) | args.yaml |
| AMP | true | args.yaml |
| GPU | NVIDIA GeForce RTX 3060 (12GB) | baseline_run_info.json |
| Python · PyTorch | 3.14.4 · 2.14.1+cu130 | baseline_run_info.json |
| Ultralytics Version | 8.4.175 | baseline_run_info.json |
| 학습 시작 · 종료 시간 | 2026-10-16 11:29:13 → 11:36:58 (7.7분) | baseline_run_info.json |
| Run 폴더 | runs/baseline_v1/ (results.csv · args.yaml) | |
| Best Weight | models/baseline/baseline_best.pt (= runs/baseline_v1/weights/best.pt) | |

## 2. 데이터 사용 확인

- [x] 학습은 **Train 600장**만 사용
- [x] Best epoch 선택 · 평가는 **Val 75장**만 사용
- [x] **Test (Frozen, 75장) 미사용** (`test_bridge_used: false`, 07 은 `allow_test=False`)
- [x] **Bridge Holdout (150장) 미사용** (dataset.yaml 에 없음)
- [ ] 참고: manifests 에 `eval_exclude=True` 가 5장(val 4 · test 1) 표시되어 있지만, 현재 학습 · 평가 코드는 이 열을 읽지 않음 → **Val 75장 전체로 평가** (val 4장은 train 과 거의 같은 사진이라 점수가 약간 높게 나올 수 있음)

## 3. 학습 경과 (runs/baseline_v1/results.csv)

| 항목 | 값 |
|---|---|
| 진행 epoch | 70 / 70 (Early Stopping 발동 안 함) |
| Best epoch | **49** (fitness = 0.1·mAP50 + 0.9·mAP50-95 최고) |
| Best epoch 값 (학습 중 val) | P 0.891 · R 0.592 · mAP50 0.658 · mAP50-95 0.511 |
| 마지막 epoch (70) | mAP50-95 0.485 |
| 메모 | 50 epoch 전후로 수렴 (이후 0.48~0.50) · 61 epoch 부터 train loss 급감은 close_mosaic 영향 (val 개선 없음) |

## 4. 결과 (07_evaluate_baseline.py · Val 75장 · best.pt)

**전체** — reports/baseline_metrics.csv

| Split | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| val | 0.890 | 0.592 | 0.658 | 0.505 |

**Class별** — reports/baseline_class_metrics.csv

| Class | Precision | Recall | mAP50 | mAP50-95 | 메모 |
|---|---|---|---|---|---|
| 0 leaf_paper | 0.735 | 0.621 | 0.715 | 0.589 | |
| 1 plastic_stone_metal | 0.838 | 0.690 | 0.779 | 0.664 | |
| 2 branch | 0.888 | 0.649 | 0.792 | 0.605 | Val 박스의 64% (205/318) → 전체 Recall 좌우 |
| 3 insect | 0.987 | 1.000 | 0.995 | 0.666 | Val 박스 10개뿐 (변동 큼) |
| 4 rubber_glove_unused | N/A | N/A | N/A | N/A | 미사용 Class |
| 5 disease_browning | 1.000 | **0.000** | 0.009 | 0.003 | **미검출** (예측이 거의 없어 P=1 은 착시) |
| 6 green_onion_pepper | N/A | N/A | N/A | N/A | Val 에 없음 (희소 Class → Train 보호) |

**그래프** — reports/figures/baseline_results.png · baseline_confusion_matrix.png

**요약**
- 오탐은 적지만(P 0.89) 이물의 약 40% 를 놓침(R 0.59) → 개선 방향은 **Recall**
- Class 5 병해 · 갈변 Recall 0: Train 에 170개뿐이고 대부분 작은 박스 (size_distribution.csv: train small 60.6% · large 2.4%, 큰 갈변은 대부분 Bridge 로 배정) → 실패 분석 1순위

## 5. 이전 실행 비교 (같은 데이터 · 학습 중 val best epoch 기준)

| 실행 | imgsz | batch | epochs | best epoch | mAP50-95 | 시간 |
|---|---|---|---|---|---|---|
| 10-15 1차 | 640 | 8 | 50 | 36 | 0.486 | 5.5분 |
| 10-16 2차 | 640 | 16 | 100 | 85 | 0.516 | 9.2분 |
| 10-16 3차 | 960 | 16 | 100 | 71 | 0.601 | 12.4분 |
| **10-16 최종 (본 문서)** | 640 | 8 | 70 | 49 | 0.511 | 7.7분 |

- 640 에서는 batch · epoch 를 바꿔도 0.49~0.52 → 성능을 가르는 건 **imgsz** (960 은 개선 실험 후보)
- 2차 · 3차 실행 결과는 같은 `runs/baseline_v1` 에 덮어써져 weights 가 남아 있지 않음 (숫자만 기록)

## 6. 확인 · 수정 필요

- [ ] **팀 계획과 조건이 다름**: 팀 계획(PR #51 리뷰)은 batch 16 · epochs 100 · patience 30, 본 Baseline 은 batch 8 · epochs 70 · patience 30 → 팀 합의 필요 (성능은 2차 0.516 vs 최종 0.511 로 거의 같음)
- [ ] **07 CONFIG 기록값 불일치**: `reports/baseline_metrics.csv` 의 batch · epochs 열이 `16 · 100` 으로 적혀 있음 (07_evaluate_baseline.py 의 CONFIG 기록용 값). 실제 학습은 `8 · 70` → 07 CONFIG 를 맞추고 07 재실행 필요
- [ ] 개선 실험은 Baseline 을 덮어쓰지 않게 **별도 이름**(예: runs/exp001 · models/improved/exp001_best.pt)으로 저장

## 7. 메모

- Smoke Test: reports/smoke_test.md 참고 (960 · batch 16 · 3 epoch GPU 최대 4.86GB / 12GB)
