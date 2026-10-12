# 2조 Project Baseline

이 문서는 우리 팀이 교과 7 조각김치 이물검출 라벨링 프로젝트를 어떤 기준으로 진행하는지 정한 공통 규칙입니다.

## 1. 공통 데이터 기준

- 전체 이미지: 900장 (4K JPG) + YOLO TXT 900개
- 출처: 이물검출_학습데이터1 (train), 이물검출_학습데이터2 (train · validation)
- Label Format: YOLO TXT (`class_id x_center y_center width height`, 0~1 정규화)
- Class: 0~6 (번호 변경 금지), Class 4 고무장갑은 사용하지 않음 → 발견 시 REVIEW
- Class 설정 파일: `configs/classes.yaml`
- RAW 데이터: 수정 금지 (SHA-256 해시로 검증, `scripts/00_raw_snapshot.py`)
- 데이터: AI캠퍼스 교육용 100% 가상 생성 데이터, NDA 대상

## 2. 우리 팀 작업 기준

| 역할 | 이름 | 담당 |
|---|---|---|
| PM / Integrator | (이름) | 일정·배분, Git, FINAL 생성 |
| GUI / Image | (이름) | 화면 버그, 실행 캡처·시연, README |
| BBox / Coordinate | (이름) | 좌표 버그, BBox 기준서 |
| Label / Storage | (이름) | 저장 로직, classes.yaml, 내보내기 스크립트 |
| QA / Validation | (이름) | Validation, Golden·Pilot·Acceptance, Test Report |
| Data / Document | (이름) | Manifest, Class 기준서, QA Summary, Handoff |

- 1차 라벨 검수: 6명 전원, 1인 150장 (`scripts/03_assign.py` 로 Dataset/split 이 고르게 배분)
- 교차검수: 각 작업자의 다음 순번 1명 (EDITED · REVIEW · Class 4 · 빈 TXT 100%, PASS 25% 표본)
- REVIEW 최종 판단: PM + QA (2인 판정, Note 에 근거 기록)
- 상태: PENDING → PASS / EDITED / REVIEW → REVIEWED → FINAL

## 3. 저장 위치

| 구분 | 위치 | Git |
|---|---|---|
| 원본 RAW | `~/kimchi_data/raw/` (6명 모두 같은 경로) | 제외 |
| 작업 중 WORK | `data/work_raw/` (수정 TXT + manifest.csv) | 제외 |
| 최종 FINAL | `data/final/images/`, `data/final/labels/` | 제외 |
| 제출 Manifest | `manifests/dataset_manifest.csv` | 포함 |

## 4. Git 작업 기준

```text
기능 하나 구현 또는 버그 하나 수정
→ 직접 실행
→ tests/test_core.py, scripts/09_golden_test.py 통과
→ Commit
→ 다음 작업
```

Commit 메시지는 무엇을 했는지 알 수 있게 씁니다.

```text
feat: configs/classes.yaml 에서 Class 목록 읽기
fix: Zoom 상태에서 새 BBox 저장 위치 오류 수정
docs: Class 기준서 작성
```

`update`, `수정`, `최종` 처럼 내용을 알 수 없는 메시지는 쓰지 않습니다.
10/7 Feature Freeze 이후에는 버그 수정과 산출물 보완만 커밋합니다.

## 5. 프로젝트 완료 기준

- 900장 전체 검수 완료 (PENDING 0)
- 미처리 REVIEW: 0건, 교차검수 안 된 EDITED: 0건
- Validation CRITICAL: 0건
- 이미지와 TXT Pair 확인 완료
- RAW 변경: 0 (해시 검증)
- FINAL 데이터 정리 완료 (`scripts/07_build_final.py` 성공)
