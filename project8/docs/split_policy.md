# Split 정책 및 버전 변경 기록

- 기준일: 2026-10-19 
- 작성자 : 장세훈(Dataset-audit 담당)
- Policy Version : `group_fixed_v4` · Dataset Version : `kimchi_v4` · 대상: 교과 7 FINAL 900장
- 실행 : `scripts/03_build_split_v4.py`

## 1. 그룹 분할 정책 (v4-B)

| 항목 | 결정·적용 방식 |
|---|---|
| 기본 묶음 | 파일명 시계열에서 Δt > 300초로 18개 구성 |
| 그룹 관계 | MD5 동일 파일 병합, 같은 위치·다른 Class 배치 후보 점검 기능 유지 |
| 육안 확인 | Human QA 를 통해 그룹별 이물 구성·유사 장면 확인. T17은 단독 장면, T12·T13은 Class 0·1 구성 비교 대상으로 기록 |
| 배정 단위 | 확정된 그룹 전체 |
| 직접 배정 | Val=T01·T03·T07 / Test=T08·T14 / Bridge=T09·T11·T16 / 나머지 Train |
| 수량 | Train 609 / Val 66 / Test 75 / Bridge 150. 배정 결과의 수량이 표와 다르면 실패 |
| 평가 기준 | Class 0·1·2·3·5·6 검사. Val·Test 각각 BBox 5개 미만이면 정책상 평가 불가. Class 4는 미사용 |
| 장면 확인 | 없는 장면의 검출 성능을 있는 것처럼 보고하지 않음 |
| 크기 집계 | 긴 변 640px 환산 √BBox 면적, Class별 3분위 구간. 물리적 절대 크기와 구분 |
| 품질 확인 | 출처 비율·날짜 다양성·애매한 라벨은 검사 |
| 평가 제외 | T08의 애매한 라벨 1장에 eval_exclude 표시. 실제 평가에서도 제외하여 구분 |
| 보존 | RAW·FINAL 보호, Bridge는 dataset.yaml에서 제외. 기존 결과 이동 후 새 결과 저장·복사 |

## 2. Split 역 정의

Train
- 모델 학습용. 

Validation
- 기존 Dataset 2 / validation을 우선 후보로 검토.
- Baseline과 Improved 비교에 사용.

Frozen Test
- Final Model을 Validation 한 뒤 Final 성능 확인용 평가에 쓰임.

Bridge Holdout 
- 교과 8 Train / Validation / Frozen Test와 별도 분리.
- 교과 8 학습·튜닝·모델 선택에 사용하지 않음.
- 교과 14 Final Model 연결 성능 확인용으로 보존.

## 3. split 역할 배정

| split | 그룹 | 이미지 수 |
|---|---|---:|
| Train | T00·T02·T04·T05·T06·T10·T12·T13·T15·T17 | 609 |
| Val | T01·T03·T07 | 66 |
| Frozen Test | T08·T14 | 75 |
| Bridge | T09·T11·T16 | 150 |
| 합계 | 18개 그룹, T17 전체 Train | 900 |

- 세부 수량·분포·검증 증거는 [reports/split_report.md] 참조.

## 4. split_manifest.csv 필드 설명

- 가이드 기준 `image_path` 필드는 팀 산출물 기준 `relative_path`로, `label_path`를 `label_relative_path`로 연결. 
  반면, `yolo_image_path`와 `yolo_label_path`는 **분할 결과가 놓일 경로**
- `capture_group` 은 `group_id`-병합 과정을 거친 배정 묶음으로 연결. ( 다만 코드상 `time_group`은 최초 시간 묶음 )

## 5. 문제와 한계

| 항목 | 현재 상태·대응 |
|---|---|
| **Class 6·대상 단독·정상 장면의 평가 표본 부족** | Class 6은 Val·Test 각 1개로 평가 불가. 대상 단독은 T17 전체 Train이라 Val·Test 0장. 정상 김치는 Test 0장으로 Val 15장의 오탐만 확인 가능 |
| **Class·출처·크기 분포 편중** | Val Class 1은 56.6%, Dataset 1은 83.3%. Bridge Class 5는 236개로 Train 163개보다 많음. Bridge Class 0 small 81.6%, Test Class 2 medium 63.8%. Class·크기별 지표와 표본 수를 함께 보고 |
| **코드·저장 결과의 버전 혼재** | 실행 스크립트는 v4-B이나 기본 정책에는 v5 후보(T06 Bridge, 151장)와 Train Class 최다 검사가 추가됨. v4-B 실행이 배정·수량은 덮어써도 최다 검사는 상속하여 Class 5에서 실패 가능. 공유 Manifest·CSV는 아직 kimchi_v1. 동기화·검증 차단 동작 확인 전 첨부의 ‘14개 통과’를 현행 코드 재검증으로 취급하지 않음 |


## 부록. 버전별 문제와 조치

v0.6~v3는 기존 변경 원자료, v4 탐색판~v4-B는 이번 첨부 자료 기준. 한계는 최종 v4-B에 통합.

### v0.6 → MVP

| 문제·원인 | 다음 버전의 조치 |
|---|---|
| 무작위 seed 0~1999에서 배정 조건 충족 실패 | 장수에 맞는 그룹 조합을 탐색하는 결정적 방식으로 전환 |
| 점수가 장수·출처 차이에 치우쳐 장면·Class 다양성을 반영하지 못함 | 장면 최빈값 × Class 다양성으로 층(stratum)을 만들고 분포 차이를 점수화 |
| 25장 블록 경계에서도 같은 이물이 이어짐 | 5분 간격의 18개 묶음을 기본 단위로 사용 |

### MVP → v2

| 문제·원인 | 다음 버전의 조치 |
|---|---|
| 층 점수만으로 Class·배경 편중을 제어하지 못함 | Class·배경 점수, Val/Test 최소 객체 수, Train 우선 조건과 완화 순서 추가 |
| 원본 validation 활용과 Val의 정상·단독 장면 구성을 요구 | val-first 조각 배정은 누수로 폐기. 그룹 단위 가산점·정상 장면 고정 도입. 단독 장면에는 T17 일부 분리 예외를 별도로 도입 |
| 객체 크기와 같은 위치의 반복 배치를 조사하지 않음 | 크기 분포 집계, 박스 배치 IoU 기반 후보 탐지·병합 추가 |
| 18개 묶음에서 조합 탐색이 오래 걸림 | 3분 간격의 29개 묶음을 시도하고, 장수 합이 맞는 조합만 탐색 |

### v2 → v3

| 문제·원인 | 다음 버전의 조치 |
|---|---|
| 3분 경계가 같은 이물 묶음을 나눔 | 5분 간격·18개 기본 묶음으로 복귀 |
| 공통 크기 구간에서 Class 5가 small에 집중 | Class별 3분위 크기 구간(class_quantile)으로 변경 |
| 그룹 번호와 비슷한 후보 점수에 따라 고정 대상·결과가 달라짐 | 자료상 장면명 기반 Val 지정·역할별 결과 고정 도입 |
| Class 편중과 미확인 유사 이미지 존재 | Class 가중치 1→3, 별도 pHash 점검과 평가 제외 표시 도입 |

### v3 → v4 탐색판

| 문제·원인 | 다음 버전의 조치 |
|---|---|
| T17 일부를 T17_V로 분리해 Train·Val에 같은 이물 세트 배정 | T17 150장 전체를 Train에 두고 조각 생성 제거 |
| same_bundle_split 행을 검증에서 제외 | 기본 묶음·최종 그룹의 단일 split 배정을 예외 없이 검사 |
| T02의 정상 김치 10장을 Val로 보내 Train 배경 표본이 줄어듦 | T02는 Train으로, T01 1장·T03 39장·T07 26장은 Val로 이동 |
| 묶음을 유지하면서 기존 Val 75장을 맞추기 어려움 | Val 66·Train 609로 수량 변경. 당시에는 조합 탐색·점수·완화 조건 유지 |

### v4 탐색판 → v4-B 최종

| 문제·원인 | 다음 버전의 조치 |
|---|---|
| 배정이 정해진 뒤에도 탐색·점수·완화 처리가 남음 | assignment 표대로 직접 배정. 없는 묶음·중복 지정·수량 불일치는 오류 처리 |
| 출력이 kimchi_v4 별도 경로에만 저장되어 후속 코드의 기본 경로와 다름 | 기존 manifests·reports·data·configs 경로 사용. 먼저 검사 후 기존 결과를 backup/split_<시각>/로 이동 |
| Class·장면별 평가 가능 여부와 크기 편중이 드러나지 않음 | coverage·size_distribution 출력 추가. 표본 부족은 평가 불가로 기록 |
| 별도 pHash 점검에 T17_V 전용 처리가 남음 | 첨부 기록상 v4 점검을 경계 검사와 다른 split의 유사 쌍 검사로 정리 |
