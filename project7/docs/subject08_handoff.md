# Subject 07 → Subject 08 Handoff

> 교과 7 에서 검수를 끝낸 조각김치 이물검출 YOLO Dataset 을 교과 8 학습에 바로 쓸 수 있게 정리한 인수인계서입니다.
> 자동 생성: `python scripts/08_handoff.py` (FINAL 생성 후) · 숫자는 FINAL 기준 자동 집계 · 데이터는 100% 가상 생성 교육용 · NDA

## 1. Handoff 목적

- 교과 7 FINAL 900장(JPG + YOLO TXT)과 기준 문서를 교과 8 YOLO11n 학습의 입력으로 전달합니다.
- 교과 8 은 이 데이터를 **다시 라벨링하지 않고** 그대로 받아 Data Audit → Split → 학습으로 이어갑니다.

## 2. FINAL Dataset

| 항목 | 값 |
|---|---:|
| FINAL 이미지 | TBD (FINAL 후 08_handoff.py 가 채움) |
| FINAL 라벨(TXT) | TBD (FINAL 후 08_handoff.py 가 채움) |
| 빈 TXT (정상 김치 · Negative) | TBD (FINAL 후 08_handoff.py 가 채움) |
| 전체 BBox | TBD (FINAL 후 08_handoff.py 가 채움) |
| 작은 이물 (노트 `small`) | TBD (FINAL 후 08_handoff.py 가 채움) |
| 남은 REVIEW | TBD (FINAL 후 08_handoff.py 가 채움) |
| Class 4(고무장갑) 라벨 | TBD (FINAL 후 08_handoff.py 가 채움) |

- Label Format: YOLO Detection TXT · 이미지와 TXT 는 **같은 파일명 Pair**

FINAL 위치 (사진은 내부 저장 · Git 금지 / 라벨 · 장부는 Git):

```
data/final/
├── images/           ← FINAL 이미지
├── labels/           ← 같은 이름의 YOLO TXT
├── manifest_final.csv  ← 900장 상태 · 출처 · split · scene_type
├── final_file_map.csv  ← 원래 경로 ↔ FINAL 파일명 대응
└── FINAL_INFO.json     ← 생성 시각 · 수량 · 수정 금지 안내
```

- 교과 8 쪽 위치: `project8/data/subject7_final/` 로 복사해서 사용 (원본처럼 보호, 덮어쓰지 않음)

## 3. YOLO Label Format

TXT 한 줄 = 객체 하나

```
class_id x_center y_center width height
6 0.800620 0.623148 0.034091 0.053704
```

- 좌표는 픽셀이 아니라 이미지 크기 대비 **0~1 비율** → 학습 해상도(imgsz)를 바꿔도 라벨은 그대로
- 빈 TXT 는 오류가 아니라 사람이 확인한 정상 이미지(Negative)

## 4. Class 정보 (번호 변경 금지)

| ID | 이름 | 사용 | FINAL BBox 수 |
|---:|---|---|---:|
| 0 | 나뭇잎·종이류 | 사용 | TBD |
| 1 | 플라스틱·돌·금속 | 사용 | TBD |
| 2 | 나뭇가지류 | 사용 | TBD |
| 3 | 벌레류 | 사용 | TBD |
| 4 | 고무장갑(미사용) | 사용 안 함 (배경 · 라벨 0건이어야 함) | TBD |
| 5 | 병해·갈변 | 사용 | TBD |
| 6 | 파·고추 | 사용 | TBD |

- **배경 (Class 없음)**: 김치(잎 · 조각 · 양념)와 고무장갑에는 BBox 가 없습니다. 모델은 이 부분을 "이물이 아닌 것"으로 배웁니다.
- Class 4 는 번호 체계 유지를 위해 `dataset.yaml` 에 남기되 라벨은 0건입니다. 모델이 Class 4 를 예측하면 FP 로 확인합니다.
- 작아도 확실한 이물은 BBox + 노트 `small` (스티로폼 = Class 1) → 교과 8 실패분석에서 "작은 이물 FN" 근거
- 상세 기준: `docs/class_guide.md` (v1.7.1) · 프로그램 설정: `configs/classes.yaml`

## 5. BBox 기준

- 객체 외곽에 밀착 (여백 최대 3px, 잘림 금지) · 하나의 객체 = BBox 1개 · 가려져 끊겨 보여도 같은 객체면 1개
- 상세 기준: `docs/bbox_guide.md` (v1.2)

## 6. QA 결과

- 작업 상태: TBD (FINAL 후 08_handoff.py 가 채움)
- 목표: REVIEW 0 · CRITICAL 0 · Pair 오류 0 (07_build_final 은 이 조건을 만족해야만 FINAL 을 만듦)
- 검수 과정: 1차 라벨링 → 교차검수 → 확인 필요(REVIEW) 최종검수 → 전체 900장 최종검수(3명, 이전 검수자와 겹치지 않게)
- 상세: `reports/qa_summary.md` · 프로그램 테스트: `reports/test_report.md` · 코드 리뷰: `docs/code_review.md`

## 7. Dataset 작업 이력

- `manifests/dataset_manifest.csv` (10_export_manifest.py) · FINAL 쪽은 `manifest_final.csv`
- 확인 가능: 원본 출처(source_dataset) · 기존 split(original_split) · scene_type · 작업자 · 검수자 · 상태 · REVIEW 사유 · 노트(small 등)

- Dataset / 기존 split: TBD (FINAL 후 08_handoff.py 가 채움)

- scene_type: TBD (FINAL 후 08_handoff.py 가 채움)

## 8. 교과 8 전달 자료

```
FINAL 폴더 (내부 저장 · USB / 공유폴더로 전달)
├── images/ · labels/ · manifest_final.csv · final_file_map.csv · FINAL_INFO.json
Git (project7/)
├── docs/subject08_handoff.md   ← 이 문서
├── docs/class_guide.md · docs/bbox_guide.md
├── configs/classes.yaml
├── manifests/dataset_manifest.csv
└── reports/qa_summary.md · reports/test_report.md
```

- 원본 김치 사진(JPG)은 GitHub · 디스코드 · 카톡에 올리지 않습니다 (NDA). 사진 전달은 USB · 공유폴더 · 메일(작은 zip)만 · 라벨 TXT · CSV 는 Git 허용.

## 9. 교과 8 에서 먼저 확인할 것 (1~2일차)

- [ ] 이미지 수 = TXT 수 = 900, 같은 이름 Pair
- [ ] Class 0~6 · Class 4 라벨 0건 · 범위 밖 Class 0건
- [ ] 좌표 0~1 · 너비/높이 > 0
- [ ] 빈 TXT 수가 manifest 의 정상 김치(normal_kimchi)와 맞는지
- [ ] source_dataset / original_split / scene_type 분포 확인 (위 7장 표) · scene_type "(미기록)" 이 있으면 교과 7 WORK 에서 채운 뒤 FINAL 재생성
- [ ] **capture_group**(같은 촬영 묶음) 정하기: 파일명이 `YYMMDD_HHMMSS…` 형태 → 같은 날짜·가까운 시각 = 같은 묶음 후보. 촬영 묶음인지 먼저 확인하고 가정하지 않기
- [ ] 기존 Dataset 2 / validation 은 Validation 후보로 우선 검토 (교과 8 수행가이드 11.2)
- [ ] Train / Validation / Frozen Test / **Bridge Holdout(교과 14 보존)** 을 같은 capture_group 이 섞이지 않게 나누기

## 10. 교과 8 연결 흐름

```
교과 7 FINAL 900장
  → Pair · Class · 좌표 확인 (dataset_audit)
  → manifest 로 출처 · split · scene_type · capture_group 확인
  → Train / Val / Frozen Test / Bridge Holdout 확정 (split_builder)
  → dataset.yaml (Class 0~6 그대로)
  → Smoke Test → Baseline 학습 → Validation → 실패분석 → 한 변수 개선
  → Final Model → Frozen Test → Detection · Auto Label (교과 7 라벨러로 Human Review)
```

## 11. 교과 8 주의사항

- 교과 7 에서 기존 train / validation 을 섞지 않았습니다. 최종 split 은 교과 8 에서 결정합니다.
- object_only 이미지 성능이 김치 배경 성능을 보장하지 않습니다. scene_type 별로 따로 평가하세요.
- 비슷한 장면이 여러 split 에 나뉘면 Data Leakage → capture_group 단위로 나누세요.
- 작은 이물(`small`)은 imgsz 640 에서 놓칠 수 있습니다 → 실패분석 · imgsz 개선 실험 후보.
- 라벨 오류를 발견하면 FINAL 을 직접 고치지 않고 교과 7 WORK 에서 수정 → Validation → FINAL 재생성 → Dataset Version 올리기 (kimchi_v1 → v2).
- Auto Label 결과는 교과 7 라벨링 프로그램(`bash run.sh`)으로 사람이 검수한 뒤에만 정답으로 씁니다.
