# 01 Project Baseline — 2조 공통 기준

> 📍 [README](../README.md) › docs › **01 Project Baseline** · → [02 Class 기준서](02_class_guide.md)
> 담당 PM · Manifest · 마지막 수정 2026-10-15

## 한눈에 보기

- **대상**: 조각김치 4K JPG **900장** + YOLO TXT 900개 (BBox 4,399개) · Class **0~6** (4번 고무장갑은 사용 안 함)
- **방법**: 6명이 우리 프로그램으로 1차 라벨링 → 교차검수 → 최종검수 → FINAL
- **규칙**: RAW 는 절대 수정하지 않고 저장은 WORK 에만 · 사진은 Git 금지
- **완료 기준 6개** 중 5개 달성 확인 · RAW 해시 확인은 `--verify` 로 마지막 점검 (아래 5장)

## 1. 공통 데이터 기준

| 항목 | 기준 |
|---|---|
| 이미지 | 900장 (4K JPG, 4848 × 2704) + YOLO TXT 900개 |
| 출처 | 이물검출_학습데이터1 train 500 · 학습데이터2 train 220 · validation 180 |
| 라벨 형식 | YOLO TXT (Class 번호 + 중심 x · y + 너비 · 높이, 0~1 비율) |
| Class | 0~6 번호 변경 금지 · 4번 고무장갑 = 배경 (박스 없음) · 설정 `configs/classes.yaml` |
| RAW | 수정 금지 · SHA-256 해시로 확인 (`00_raw_snapshot.py`) |
| 데이터 | AI캠퍼스 교육용 100% 가상 생성 · NDA 대상 |

## 2. 역할 · 작업 기준

| 직책 | 브랜치 | 담당 |
|---|---|---|
| PM · Integrator | feature/pm | 일정 · 배분 · Git · FINAL 생성 |
| GUI · Image | feature/gui | 화면 · 캡처 · 시연 · Figma |
| Coord (BBox · Coordinate) | feature/coord | 좌표 · Golden Test · Class · BBox 기준서 |
| Storage (Label · Storage) | feature/storage | 저장 로직 · 데이터 취합 · 배포 |
| QA (Validation) | feature/qa | Validation · RAW 확인 · Test Report |
| Manifest (Document · 서기) | feature/manifest | 작업 장부 · QA Summary · Handoff · 작업 기록 |

| 단계 | 누가 | 기준 |
|---|---|---|
| 1차 라벨링 | 배정된 담당자 | 900장 전체 |
| 교차검수 | 작업자가 아닌 다른 사람 | 수정(EDITED) · 확인 필요(REVIEW) 710장 |
| 최종검수 | 3명 × 300장 | 본인이 검수한 사진은 받지 않음 |
| REVIEW 판단 | PM + QA | 노트에 근거 기록 |

상태 흐름: **대기(PENDING) → PASS / 수정(EDITED) / 확인 필요(REVIEW) → 검수 완료(REVIEWED) → FINAL**

## 3. 저장 위치

| 구분 | 위치 | Git |
|---|---|---|
| 원본 RAW | `data/raw/` | 제외 (사진) |
| 작업 중 WORK | `data/work_raw/` (고친 TXT + manifest.csv) | 제외 (작업 중) |
| FINAL | `data/final/images/` · `labels/` | 사진 제외 · 라벨 · 장부 허용 |
| 제출 Manifest | `manifests/` | 포함 |

## 4. Git 기준

- 기능 하나 또는 버그 하나 → 직접 실행 → `tests/test_core.py` 통과 → Commit
- Commit 메시지는 무엇을 했는지 보이게 (`feat:` 기능 · `fix:` 버그 · `docs:` 문서) · '수정' · '최종' 같은 말만 쓰지 않기
- main 은 PR 로만 · `git add .` 금지 · Merge 후 Delete branch 누르지 않기
- **Feature Freeze 10/13** 이후에는 버그 수정과 산출물 보완만

## 5. 완료 기준과 결과

| 기준 | 결과 |
|---|---|
| 900장 전체 검수 (대기 0) | ✅ 900 REVIEWED |
| 미처리 REVIEW 0 · 교차검수 안 된 EDITED 0 | ✅ 0 · 0 |
| Validation CRITICAL 0 | ✅ 0 ([reports/03_validation_final.csv](../reports/03_validation_final.csv)) |
| 이미지 · TXT Pair | ✅ 900쌍 |
| FINAL 생성 (`07_build_final.py`) | ✅ 900쌍 |
| RAW 변경 0 (해시 확인) | ⏳ `00_raw_snapshot.py --verify` 결과 기록 예정 |
