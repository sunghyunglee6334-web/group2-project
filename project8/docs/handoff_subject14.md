# 교과 14 Handoff — 조각김치 이물 검출 Final Model

- 작성일: 2026-10-21
- 목적: 교과 8에서 확정한 데이터·Final Model·평가·Detection·Auto Label 흐름을 교과 14에서 이어받기 위한 인계 문서
- 기준: 교과 8 Vision 객체검출 수행가이드 22.7.1 및 현재 프로젝트 8 Manifest·보고서·실행 기록

## 1. Dataset Version 및 Split

- Dataset Version: `kimchi_v4`
- Split 정책 버전: `group_fixed_v4`
- 현재 Manifest 기준 장수:

| 역할 | 장수 | Manifest |
|---|---:|---|
| Train | 609 | `manifests/train.csv` |
| Validation | 66 | `manifests/val.csv` |
| Frozen Test | 75 | `manifests/test.csv` |
| Bridge Holdout | 150 | `manifests/bridge_holdout.csv` |

- 촬영 그룹별 구성·배정 근거는 `reports/kimchi_v4/split_report.md`, 정책은 `docs/split_policy.md`에서 확인한다.
- Bridge Holdout 내부 데이터 경로는 `data/bridge_holdout/images/` 및 `data/bridge_holdout/labels/`이며 Manifest는 `manifests/bridge_holdout.csv`다. Desktop 복사본에는 이미지와 라벨 파일이 포함되어 있지 않다.
- `bridge_holdout`은 교과 8의 학습·튜닝·모델 선택·Frozen Test·시연에 사용하지 않았다. `configs/dataset.yaml`에는 Bridge를 학습·평가 split으로 넣지 않는다.
- README의 Split 표에는 이전 장수(Train 600 / Val 75)가 남아 있으나 현재 v4 Manifest와 `reports/kimchi_v4/split_report.md`는 609 / 66 / 75 / 150이다. 최신 데이터 수량은 Manifest 기준으로 읽는다.

## 2. Final Model

- Weight: `models/final/final_best.pt`
- 선택 출처: EXP003 (`models/improved/exp003_best.pt`와 같은 Weight로 기록됨)
- 모델: YOLO11n
- 추론 이미지 크기: `imgsz=1280`
- 기본 Confidence: `0.25`
- 모델 선택 시점·근거: Frozen Test 실행 전 Validation 비교로 EXP003 선택. 근거는 `reports/final_model_selection.md` 및 `reports/improvement_experiment.md`를 참조한다.
- Class ID와 이름은 교과 7의 0~6 정의를 유지한다. 번호를 재배정하지 않는다.

## 3. Frozen Test 성능 및 평가 범위 주의

현재 복사본에는 75장 기준 `reports/final_metrics.csv`, `reports/final_class_metrics.csv`와 74장 기준 `reports/final_metrics_eval74.csv`, `reports/final_class_metrics_eval74.csv`가 모두 있다.

| 평가 집합 | 이미지 수 | Precision | Recall | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|
| Test 전체 | 75 | 0.6046 | 0.4660 | 0.4934 | 0.4115 |
| eval_exclude 제외 | 74 | 0.6047 | 0.4655 | 0.4992 | 0.4171 |

- `manifests/test.csv`에서 `250411_140406550160.jpg` 1장은 `eval_exclude=True`다. `scripts/13_evaluate_final_test.py`는 Test split 평가를 수행하며 `eval_exclude` 필터를 직접 적용하지 않는다. 따라서 이 스크립트가 생성하는 75장 값과 별도의 74장 CSV는 구분한다.
- 74장 결과는 사용자가 실행했다고 확인한 `python scripts/13b_evaluate_final_test_eval74.py`의 절차로 생성됐다. 스크립트는 Manifest에서 `eval_exclude=True` 이미지명을 읽고 Test 이미지 목록에서 제외한 뒤 74장인지 확인한다. 이 목록을 임시 dataset YAML로 만들고 같은 `models/final/final_best.pt`, `imgsz=1280`, 공통 `src/evaluate_detector.py`로 평가해 두 CSV를 저장한다. 원본 Test 이미지 파일은 이동·삭제하지 않는다.
- `final_metrics.csv`는 75장 기준 요약 지표 한 행이고, `final_metrics_eval74.csv`는 eval_exclude를 제외한 74장 기준 별도 결과 한 행이다. 서로 다른 평가 범위의 산출물이다.
- 모델 선택 근거는 `reports/final_model_selection.md` 및 `reports/improvement_experiment.md`를 참조한다. Test 결과를 보고 모델·conf를 재튜닝하지 않았다.
## 4. 잘하는 상황과 알려진 약점

### 상대적으로 안정적인 영역

- Test에서 `branch`는 Precision 0.990, Recall 0.559, mAP50-95 0.806이다.
- `plastic_stone_metal`은 Precision 0.977, Recall 0.480, mAP50-95 0.633이다.
- 두 클래스는 Test 객체의 대부분을 차지하며 오검출률은 낮게 기록됐지만, Recall이 높다는 뜻은 아니다. 특히 작은 객체는 별도로 확인해야 한다.

### 약한 영역

- `disease_browning`은 Test 정답 객체 45개에서 Recall 0, mAP50-95 0.029로 대부분 놓친다.
- `leaf_paper`와 `insect`는 Recall은 각각 0.857, 0.900이나 Precision이 0.320, 0.341로 낮아 오검출이 많다.
- `green_onion_pepper`는 Test 정답 객체가 1개뿐이며 Precision·Recall 모두 0이다. 표본이 하나이므로 일반 성능으로 해석하지 않는다.
- Validation Baseline 대비 Final 비교에서 작은 객체 누락 비율은 63.9%에서 60.2%로 낮아졌지만, Final에서도 작은 객체를 놓치는 문제가 남아 있다 (`reports/fn_by_size_compare.csv`).

## 5. Frozen Test 대표 FP / FN 및 분석 근거

- `frozen_test_failures/image_failures.csv`에는 Frozen Test 75장별 집계가 있다. 전체 합계는 TP 259, FP 87, FN 93, CLASS 72, BBOX 4이며 오류 항목 합계(`n_fail`)는 256이다. 이는 이미지별 오류 집계이며 `final_metrics.csv`의 Precision·Recall·mAP와는 다른 통계다.
- `representative_failures.csv`에는 대표 사례 23건(FP 5, FN 4, CLASS 10, BBOX 4)과 근거 이미지가 있다. 이미지에는 GT/예측 박스와 사례 설명이 표시되어 있다. 일부 표본을 확인했으며, 전체 23장에 대한 별도 수작업 재판정은 하지 않았다.
- 예시: `250424_152633071901.jpg`는 GT 없는 위치에 `leaf_paper`를 confidence 0.929로 예측한 FP, `250424_150751737200.jpg`는 `branch` 누락 FN, `250424_151540089453.jpg`는 GT `branch`를 `insect`로 예측한 CLASS 사례(confidence 0.943), `250411_140005265446.jpg`는 클래스는 맞지만 IoU 0.473인 BBOX 사례다. CSV의 원인 설명 중 “추정” 또는 “그림 확인 필요”로 표시된 내용은 확정 원인으로 해석하지 않는다.
- 대표 사례 21번 `250411_140406550160.jpg`는 `manifests/test.csv`에서 `eval_exclude=True`다. 이 행은 실패 분석 파일에는 포함되어 있으므로 유효 Frozen Test 대표 사례와 구분해야 한다. 이 1장을 이미지별 집계에서 제외하면 TP 256, FP 87, FN 90, CLASS 72, BBOX 3, 오류 합계 252다. 이 수치만으로 74장 Precision·Recall·mAP를 계산할 수는 없다.
- 대표 CSV의 `evidence` 경로(`reports/frozen_test_failures/images/...`)와 실제 폴더 위치(`project8/reports/frozen_test_failures/images/`)가 일치한다.
- Validation 작은 `leaf_paper` FN 분석은 별도 자료인 `reports/failure_analysis.csv`, 모델별 비교는 `reports/failure_compare.csv` 및 `reports/fn_by_size_compare.csv`다. Validation 사례를 Frozen Test 사례와 혼동하지 않는다.
## 6. Detection 시연

- 실행 위치: `project8/` 루트
- 실행 명령: `python scripts/14_predict_images.py`
- 기본 입력: `data/test_detection/`
- 저장 위치:
  - 시각화 결과 이미지: `demo/prediction_images/`
  - 추론 상세 CSV: `demo/prediction_images/inference_results.csv`
- 현재 CSV에는 `250424_160002175452.jpg` 1장과 검출 3건이 기록되어 있다(벌레 2개, 나뭇가지 1개). 기록된 Confidence는 약 0.922, 0.868, 0.800이다.
- Final Model 확정 및 Frozen Test 검토 단계에서는 Evaluation·Experiment 담당이 함께 결과를 검토했다. Inference 단계는 Detection 기능 실행과 저장 결과를 확인했으며, 라벨 정합성이나 모델 성능을 다시 검수하는 단계로 진행하지 않았다. 현재 Desktop 복사본에는 원본·결과 JPG가 없고 CSV만 있으므로, 이 문서를 작성하며 이미지를 다시 열어 검수하지 않았다.
- Detection은 성능 평가와 분리된 시연이다. 출력 이미지/CSV를 학습용 정답이나 평가 결과로 취급하지 않는다.

## 7. Auto Label 및 Human Review 시연

### 실행과 산출 경로

- 프로젝트 루트에서 `python scripts/15_auto_label.py`를 실행한다. 한 장만 처리할 때는 `python scripts/15_auto_label.py --input data/test_detection/파일명.jpg`를 사용한다.
- 입력 기본값: `data/test_detection/`
- 최종 Weight·설정: `models/final/final_best.pt`, `imgsz=1280`, 기본 conf `0.25`
- 자동 생성 후보 TXT: `demo/auto_label/candidate_labels/*.txt`
- 실행 결과 CSV: `demo/auto_label/candidate_labels/auto_label_results.csv`
- 교과 7 라벨링 GUI에서 후보를 열어 검수한 TXT: `demo/auto_label/reviewed_labels/*.txt`
- 후보 실행 및 Human Review 추적: `reports/auto_label_review.csv` (후보 실행 시 행을 만들고, GUI 저장 시 같은 행의 검수 결과를 갱신)

### 현재 기록된 처리 결과

- 입력 `data/test_detection/250424_160002175452.jpg` 1장을 처리했고 `auto_label_results.csv` 상태는 `OK`다.
- 후보는 BBox 3개, 실행 시간 1.513116초다. 후보 TXT는 3행이며 좌표는 YOLO 정규화 형식으로 저장되어 있다.
- Human Review에서 Class 5 라벨 1개를 추가해 최종 4개로 저장했다. 클래스 수정·기존 BBox 수정·삭제는 각각 0건이다.
- `auto_label_review.csv`에는 `APPROVED_EDITED`, 후보 3 / 최종 4, 추가 1, 검수 1회, 담당 `kjh`가 기록되어 있다.
- 이 수치는 후보·검수 파이프라인의 실행·저장 기록이지, GT와 비교해 산출한 모델 정밀도/재현율은 아니다. 원본 이미지가 없는 복사본에서 시각적으로 옳은 라벨인지 재검수하지 않았다.

## 8. 교과 14에서 이어갈 작업

1. `reports/frozen_test_failures/`의 이미지별 실패 집계와 대표 이미지 사례를 참조한다. 대표 사례 중 `eval_exclude=True`인 1건은 74장 기준 사례와 구분한다.
2. 75장 평가는 `python scripts/13_evaluate_final_test.py`, eval_exclude 제외 74장 평가는 `python scripts/13b_evaluate_final_test_eval74.py`로 구분한다. 74장 실행 절차는 스크립트에 기록되어 있고 지표 CSV는 `reports/`에 저장된다.
3. 수행가이드가 정한 첫 연결점에 따라 Bridge Holdout 150장으로 교과 8 Final Model을 교과 14 환경에서 확인한다. Bridge 경로는 `data/bridge_holdout/`이며 교과 8에서는 사용하지 않은 별도 Holdout이다.
4. 교과 8 Final Model 결과와 새 교과 14 환경의 결과를 구분해 기록한다. Bridge 결과를 교과 8의 학습·튜닝·Frozen Test 결과에 합치지 않는다.
5. 실제 제품/컨베이어 조건의 새 이미지가 생기면 데이터 수집·라벨 기준·조명·카메라 거리·추론 속도 요구사항을 먼저 확인하고, 해당 교과의 평가 절차에 따라 모델 적용 여부를 판단한다.
6. Conf threshold 변경이 필요하면 허용된 Validation 자료로 근거를 마련하고 변경 전후를 기록한다. 교과 8 Frozen Test 결과를 기준으로 역으로 튜닝하지 않는다.
## 확인한 자료와 미확인 사항

- 확인 자료: `manifests/{train,val,test,bridge_holdout}.csv`, `reports/kimchi_v4/split_report.md`, `reports/final_metrics.csv`, `reports/final_class_metrics.csv`, `reports/final_metrics_eval74.csv`, `reports/final_class_metrics_eval74.csv`, `scripts/13b_evaluate_final_test_eval74.py`, `reports/frozen_test_failures/{image_failures.csv,representative_failures.csv,images/}`, `reports/final_model_selection.md`, `reports/failure_compare.csv`, `reports/fn_by_size_compare.csv`, `demo/prediction_images/inference_results.csv`, `demo/auto_label/candidate_labels/auto_label_results.csv`, 후보/검수 TXT, `reports/auto_label_review.csv`, `교과8_Final_Model_분석_팀공유.pdf`, `교과8_FrozenTest_결과검토_1020.pdf`.
- 프로젝트 README는 Dataset Version과 여러 결과를 `TBD`로 두고 Split 수량도 구버전 값이므로 이 인계서는 최신 Manifest와 보고서의 기록을 우선 인용했다.
- 실제 이미지/원본 라벨을 보지 않았고, 이 문서 작성 과정에서 추론·평가를 다시 실행하지 않았다.
- README의 Git 허용 범위 설명과 수업가이드의 NDA·공개 Git 관련 주의가 범위 면에서 다를 수 있다. 교과 14로 데이터·Weight·Prediction 파일을 옮기거나 외부 Git에 업로드하기 전 기관/강사 허용 범위를 확인한다.
