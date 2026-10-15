# 10 Subject 07 → Subject 08 Handoff

> 📍 [README](../README.md) › docs › **10 Subject 07 → Subject 08 Handoff** · ← [09 코드 공부](09_code_study.md) · → [reports/01 QA Summary](../reports/01_qa_summary.md)
> 담당 Manifest · 2026-10-14

## 한눈에 (개요)

- 교과 7 FINAL **900쌍 (BBox 4,405)** 을 교과 8 YOLO11n 학습 입력으로 넘깁니다
- 빈 TXT 26 = 정상 김치 24 + 김치 · 이물 없음(none) 2 · Class 4 라벨 0 · 미처리 REVIEW 0
- 교과 8 은 라벨을 다시 만들지 않고 **먼저 감사(Audit)** → 촬영 묶음 단위로 Split
- 라벨 오류를 찾으면 FINAL 을 직접 고치지 않고 교과 7 WORK 에서 고친 뒤 FINAL 을 다시 만듭니다

---

> 교과 7에서 검수한 조각김치 이물검출 YOLO Dataset과 데이터 기준·QA 결과를 교과 8로 전달합니다.
> 본 문서는 `reports/01_qa_summary.md` (원 자동 집계 2026-10-14 11:08, Human QA 수동 보완 11:59)와 현재 FINAL 파일을 대조해 갱신했습니다. 원본 이미지는 NDA 대상이며 외부 공개 저장소에 올리지 않습니다.

## 1. Handoff 목적

- 교과 7 FINAL을 교과 8 YOLO11n Data Audit 및 학습 입력으로 전달합니다.
- 교과 8에서는 라벨을 임의로 다시 만들지 않고 먼저 전달본을 감사한 뒤, 분할 정책을 확정합니다.
- 발견된 라벨 오류는 FINAL에서 직접 고치지 않습니다. 교과 7 WORK에서 수정·검증 후 FINAL과 버전을 갱신합니다.

## 2. FINAL Dataset 개요

| 항목 | 값 |
|---|---:|
| 이미지 | 900 |
| YOLO TXT | 900 |
| 전체 BBox (RAW → 최종) | 4,399 → 4,405 |
| 빈 TXT (BBox 0개) | 26 |
| Class 4 라벨 | 0 |
| `small` 노트가 기록된 이미지 | 0 |
| 미처리 REVIEW | 0 |

| 출처 / 기존 split | 이미지 수 |
|---|---:|
| 이물검출_학습데이터1 / train | 500 |
| 이물검출_학습데이터2 / train | 220 |
| 이물검출_학습데이터2 / validation | 180 |

| scene_type | 이미지 수 |
|---|---:|
| kimchi_with_target | 725 |
| normal_kimchi | 24 |
| object_only | 149 |
| none (김치·대상 객체 없음) | 2 |

현재 복사본의 `data/final/images/`와 `data/final/labels/`에는 각각 900개 파일이 있습니다. FINAL 전달 시 이미지와 라벨의 같은 이름 Pair, `manifest_final.csv`, `final_file_map.csv`, `FINAL_INFO.json`을 함께 확인하세요.

- 교과 8 작업본: `project8/data/subject7_final/` (전달 후 원본처럼 보존)
- 파일 수와 위 수치는 교과 7 QA Summary 기준입니다. 실제 교과 8로 옮긴 뒤 다시 Pair 및 형식 검사를 수행하세요.

## 3. YOLO Label 형식

TXT 한 줄은 객체 하나입니다.

```text
class_id x_center y_center width height
6 0.800620 0.623148 0.034091 0.053704
```

- 좌표는 픽셀이 아닌 이미지 크기 대비 0~1 정규화 값입니다.
- 빈 TXT는 파일 누락과 다릅니다. 검출 객체가 없다고 확인된 이미지의 유효 라벨일 수 있습니다.
- 빈 TXT 26장은 `normal_kimchi` 24장과 `none` 2장으로 분류되어 있습니다. 교과 8에서도 Manifest와 이미지 내용을 대조하세요.

## 4. Class 기준과 BBox 현황

| ID | 이름 | 사용 기준 | 최종 BBox |
|---:|---|---|---:|
| 0 | 나뭇잎·종이류 | 사용 | 709 |
| 1 | 플라스틱·돌·금속 | 사용 | 1,665 |
| 2 | 나뭇가지류 | 사용 | 937 |
| 3 | 벌레류 | 사용 | 378 |
| 4 | 고무장갑(미사용) | 미사용, 라벨 0건 | 0 |
| 5 | 병해·갈변 | 사용 | 465 |
| 6 | 파·고추 | 사용 | 251 |
| **합계** |  |  | **4,405** |

Class ID는 교과 7 기준을 그대로 유지합니다. Class 4는 번호 체계상 설정에 남아 있지만 학습 라벨에는 사용하지 않습니다. 김치와 고무장갑은 배경이며 BBox 대상이 아닙니다. 상세 기준은 `docs/02_class_guide.md`, `docs/03_bbox_guide.md`, 프로그램 설정은 `configs/classes.yaml`을 참조하세요.

## 5. 자동 Validation, Human Final QA 및 교차검수

### 자동 Validation 결과 (WORK 기준)

| 결과 | 건수 |
|---|---:|
| CRITICAL | 0 |
| INFO: EMPTY_LABEL | 26 |
| 미처리 REVIEW | 0 |

`EMPTY_LABEL`은 자동 코드 오류(CRITICAL)가 아니라, BBox가 없는 라벨이므로 실제 이미지에서 객체 누락 여부를 사람이 확인하라는 정보 항목입니다.

### Human Final QA 상태

수업 수행가이드는 자동 Validation과 별도로 사람의 최종 확인을 요구합니다. 확인 대상으로 새로 추가·수정한 BBox, Class 변경, 작은 객체, BBox가 많은 이미지, REVIEW 이력이 있었던 이미지, Empty TXT를 제시합니다. 특히 Empty TXT는 이미지 확인 결과 정상인지 기록해야 합니다.

자동 Validation의 `EMPTY_LABEL` 항목 중 Human QA로 확인한 두 건은 고무장갑만 있는 빈 라벨 이미지였습니다. Class 4 기준에 따라 고무장갑 BBox를 삭제하고 `scene_type=none`으로 분류했습니다. 이번 Handoff의 Human QA 기록은 이 두 건의 확인 결과입니다.

### 별도 집계인 작업 배정과 교차검수

`01_qa_summary.md` 4절은 작업 상태와 담당자별 장수, reviewer 기록을 포함한 교차검수 집계를 보여줍니다. 이 값은 Human Final QA 결과와 다른 지표입니다.

| 작업·교차검수 항목 | 결과 |
|---|---:|
| REVIEWED 상태 | 900 / 900 |
| reviewer 기록을 기준으로 한 교차검수 완료 | 900 / 900 |
| 미처리 REVIEW | 0 |
| PENDING / WORKING | 0 |
| 미검수 EDITED | 0 |
| PASS 표본검수 선정 / 완료 | 0 / 0 |
| Pilot 이미지 | 0 |

PASS 표본검수가 0/0이므로 PASS 표본검수는 수행 기록이 없습니다. 이 사실과 교차검수 완료 수치만으로 Human Final QA의 범위나 완료 여부를 대신할 수 없습니다.

세부 기록은 `reports/01_qa_summary.md`를 참조하세요. Human Final QA 대상별 결과가 보완되면 그 기록을 이 문서에도 반영해야 합니다. 기능 테스트와 코드 검토는 각각 `reports/02_test_report.md`, `docs/08_code_review.md`를 참조합니다.
## 6. 라벨 보정 집계 (RAW 대비)

| 항목 | 수 |
|---|---:|
| 그대로 유지 | 2,016 |
| 위치·크기 수정 | 2,014 |
| Class 변경 | 25 |
| 추가 | 350 |
| 삭제 | 344 |
| 전체 BBox 변화 | +6 (4,399 → 4,405) |

Class별 상세는 위 표 및 `reports/01_qa_summary.md`를 기준으로 합니다.

## 7. 출처 및 추적 정보

FINAL Manifest에서 다음 정보를 확인할 수 있습니다.

- `source_dataset`, `original_split`: 원본 데이터셋과 기존 train/validation 출처
- `scene_type`: 이미지 장면 유형
- `assignee`, `reviewer`, `status`: 작업·검수 담당 및 상태
- `issue`, `note`: 검토 사유와 기록 (`small` 등)

대표 파일은 `data/final/manifest_final.csv`, `data/final/final_file_map.csv`, `data/final/FINAL_INFO.json`입니다. 제출용 Manifest는 `manifests/dataset_manifest.csv`를 참조하세요.

## 8. 전달 자료 및 보안

교과 8에는 내부 승인된 경로로 다음을 전달합니다.

- FINAL 이미지와 YOLO TXT, FINAL Manifest와 파일 매핑 정보
- `docs/02_class_guide.md`, `docs/03_bbox_guide.md`, `configs/classes.yaml`
- `reports/01_qa_summary.md`, `reports/02_test_report.md`
- 본 Handoff 문서와 제출용 Manifest

원본 김치 이미지는 공개 GitHub, 메신저, 개인 클라우드에 올리지 않습니다. 사진이 포함된 데이터는 승인된 내부 저장·전달 방식을 따릅니다.

## 9. 교과 8에서 먼저 확인할 항목

- [ ] 전달본 이미지 900장과 TXT 900장의 이름 Pair 및 읽기 가능 여부
- [ ] Class ID 범위, Class 4 라벨 0건, 좌표·BBox 경계 유효성
- [ ] 빈 TXT 26건의 구성: `normal_kimchi` 24건과 `none` 2건, 두 `none` 이미지의 근거 확인

- [ ] 출처·기존 split·scene_type 분포가 Manifest와 일치하는지
- [ ] 동일하거나 유사한 촬영을 `capture_group`으로 묶을 수 있는지 확인 (파일명 시각만으로 단정하지 않음)
- [ ] `small` 노트가 0건임을 고려해 작은 객체 관련 데이터 근거가 필요한 경우 라벨·이미지를 직접 확인
- [ ] 기존 Dataset 2 / validation 180장을 Validation 후보로 우선 검토하되, 촬영 그룹과 분포를 확인한 뒤 정책 결정
- [ ] Train / Validation / Frozen Test / Bridge Holdout 네 역할에 900장을 각각 한 번만 배정하고 누수 방지

## 10. 교과 8 처리 흐름

```text
교과 7 FINAL
  → 파일 Pair · 라벨 형식 · Class · 좌표 감사
  → source_dataset · original_split · scene_type · capture_group 확인
  → 분할 기준과 근거 문서화 후 Split Freeze
  → Smoke Test → Baseline → Validation 평가
  → 실패 분석 → 한 변수 개선 → 같은 Validation으로 비교
  → Final Model 선택 → Frozen Test 최종 평가
  → Detection · Auto Label → 사람 검수
```

## 11. 교과 8에서 유지할 조건

- 교과 7 FINAL과 Class ID/기준 및 출처 정보를 임의로 바꾸지 않습니다.
- 비슷한 촬영 그룹이 여러 split에 섞이지 않도록 합니다. 분할 수량은 데이터 감사 후 확정합니다.
- Frozen Test는 Final Model 선택 후 최종 평가에만 사용하며, 결과를 보고 재튜닝하지 않습니다.
- Bridge Holdout은 교과 8 학습·튜닝·모델 선택·Frozen Test에 사용하지 않고 교과 14를 위해 보존합니다.
- Auto Label 결과는 정답으로 바로 확정하지 않습니다. 사람이 교과 7 라벨링 도구에서 확인한 뒤 사용합니다.




