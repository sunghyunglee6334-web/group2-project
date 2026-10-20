# Baseline 학습 조건 (baseline_v1) — 산출물 2

* 목적: 개선 실험 전 **비교 기준(Baseline)** 모델을 정하고, 같은 조건으로 다시 만들 수 있게 학습 조건 · 결과를 기록
* 기준: 2026-10-19
* 실행: `python scripts/06_train_baseline.py` → `python scripts/07_evaluate_baseline.py`
* 날짜: 2026-10-19 (학습 16:14:06 → 16:22:02, **7.9분**)

## 1. 학습 조건

| 항목 | 값 | 출처 |
|---|---|---|
| Model | yolo11n.pt (COCO 사전학습) | `BASELINE_CONFIG["model_name"]` |
| Dataset Version | kimchi_v4 | `DATASET_VERSION` |
| Dataset YAML | configs/dataset.yaml (train · val · test, **Bridge 제외**) | 03_build_split 생성 |
| Train Manifest | manifests/train.csv · 609장 · md5 `fa803448` | baseline_run_info.json |
| Val Manifest | manifests/val.csv · 66장 · md5 `e1c68baa` | baseline_run_info.json |
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
| 학습 시작 · 종료 시간 | 2026-10-19 16:14:06 → 16:22:02 (7.9분) | baseline_run_info.json |
| Run 폴더 | runs/baseline_v1/ (results.csv · args.yaml) | |
| Best Weight | models/baseline/baseline_best.pt (= runs/baseline_v1/weights/best.pt) | |

## 2. 데이터 사용 확인

- [x] 학습은 **Train 609장** (Box 2,916개)만 사용
- [x] Best epoch 선택 · 평가는 **Val 66장** (Box 256개)만 사용
- [x] **Test (Frozen, 75장) 미사용** (`test_bridge_used: false`, 07 은 `allow_test=False`)
- [x] **Bridge Holdout (150장) 미사용** (dataset.yaml 에 없음)
- [x] `eval_exclude=True` 는 test 1장뿐 (train · val 0장) → Val 66장 전체로 평가

## 3. 학습 경과 (runs/baseline_v1/results.csv)

| 항목 | 값 |
|---|---|
| 진행 epoch | 70 / 70 (Early Stopping 발동 안 함) |
| Best epoch | **50** (fitness = 0.1·mAP50 + 0.9·mAP50-95 최고, mAP50 · mAP50-95 모두 최고) |
| Best epoch 값 (학습 중 val) | P 0.916 · R 0.444 · mAP50 0.506 · mAP50-95 0.344 |
| 마지막 epoch (70) | mAP50 0.471 · mAP50-95 0.334 |
| 메모 | 30 epoch 전후로 수렴 (이후 mAP50 0.46~0.49) · 61 epoch 부터 train loss 급감은 close_mosaic 영향 (val 개선 없음) |

## 4. 결과 (07_evaluate_baseline.py · Val 66장 · best.pt)

**전체** — reports/baseline_metrics.csv

| Split | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| val | 0.917 | 0.444 | 0.506 | 0.345 |

**Class별** — reports/baseline_class_metrics.csv

| Class | Precision | Recall | mAP50 | mAP50-95 | 메모 |
|---|---|---|---|---|---|
| 0 leaf_paper | 0.838 | 0.556 | 0.710 | 0.543 | Val 박스 27개 |
| 1 plastic_stone_metal | 0.940 | 0.586 | 0.680 | 0.491 | Val 박스의 57% (145/256) → 전체 Recall 좌우 |
| 2 branch | 0.786 | 0.564 | 0.657 | 0.473 | Val 박스 39개 |
| 3 insect | 0.936 | 0.957 | 0.986 | 0.559 | Val 박스 23개 |
| 4 rubber_glove_unused | N/A | N/A | N/A | N/A | 미사용 Class |
| 5 disease_browning | 1.000 | **0.000** | 0.003 | 0.001 | **미검출** (예측이 거의 없어 P=1 은 착시) |
| 6 green_onion_pepper | 1.000 | **0.000** | 0.000 | 0.000 | Val 박스 **1개뿐** → 지표 의미 없음 |

**그래프** — reports/figures/baseline_results.png · baseline_confusion_matrix.png

**요약**
- 오탐은 적지만(P 0.92) 이물의 약 56% 를 놓침(R 0.44) → 개선 방향은 **Recall**
- Confusion matrix: plastic_stone_metal 145개 중 39개(27%), disease_browning 21개 중 17개(81%) 를 배경으로 놓침
- Class 5 병해 · 갈변 Recall 0: Train 에 163개뿐이고 대부분 작은 박스 (size_distribution.csv: train small 62.0% · large 3.1%, 큰 갈변(large 62.3%)은 대부분 Bridge 로 배정) → 실패 분석 1순위
- F1 최대 0.50 (conf 0.491) · 현재 예측 기준 `PRED_CONF` 는 0.25

## 5. 확인 · 수정 필요

- [ ] **팀 계획과 조건이 다름**: 팀 계획(PR #51 리뷰)은 batch 16 · epochs 100 · patience 30, 본 Baseline 은 batch 8 · epochs 70 · patience 30 → 팀 합의 필요
- [ ] **커밋 필요**: manifests/*.csv · configs/dataset.yaml
- [ ] 개선 실험은 Baseline 을 덮어쓰지 않게 **별도 이름**(예: runs/exp001 · models/improved/exp001_best.pt)으로 저장

## 6. 메모

- Smoke Test: reports/smoke_test.md 참고 (1280 · batch 16 · 3 epoch GPU 최대 9.02GB / 12GB)
