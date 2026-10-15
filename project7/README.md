# 조각김치 이물검출 라벨링 프로젝트 (교과 7) — 2조

> **한 줄 요약** — 조각김치 4K 사진 **900장**의 기존 YOLO 라벨(**BBox 4,399개**)을 우리가 만든 라벨링 프로그램으로 6명이 나눠 검수했습니다. 원래 박스의 **54%(2,383개)를 고치고 350개를 새로 그려**, 교과 8 YOLO 학습에 바로 쓰는 **FINAL 데이터 900쌍(BBox 4,405개)** 을 만들었습니다. 900장 모두 사람 검수를 마쳤고, 자동 검사 오류(CRITICAL)는 **0건**입니다.

![프로그램 실제 작동 화면](docs/images/gui_main.png)

*사진은 NDA 때문에 흐리게 처리했고, 노란 박스는 팀이 검수한 실제 BBox 입니다.*

---

## 1. 개요

**왜 만들었나** — 강사님이 주신 조각김치 이물검출 데이터(4K JPG 900장 + YOLO TXT 900개)에는 틀리거나 빠진 라벨이 섞여 있었습니다. 이대로 학습하면 모델이 틀린 것을 배웁니다. 그래서 **사람이 한 장씩 확인하고 고칠 수 있는 프로그램**을 직접 만들고, 6명이 같은 기준서로 검수했습니다.

**무엇을 만들었나** — Tkinter 라벨링 프로그램(v2.2) 1개, 운영 스크립트 11개(00~10), 기준서 2개(Class v1.7.2 · BBox v1.2), FINAL 데이터 900쌍, 교과 8 인계 문서입니다.

**결과는 어떻게 나왔나** — 900장 중 **778장(86%)** 의 라벨을 고쳤습니다. 박스 2,014개는 위치 · 크기를 다듬었고(그중 1,857개는 10px 이내 미세 조정), 25개는 Class 를 바꿨고, 344개는 지웠고(고무장갑 등 오표기), 350개는 새로 그렸습니다(놓친 이물).

**무엇이 더 좋아졌나** — 놓쳤던 **병해 · 갈변(Class 5)** 이 313 → **465개(+49%)** 로 늘었고, 이물이 아닌데 박스가 있던 **플라스틱 · 돌 · 금속(Class 1)** 오표기가 1,831 → **1,665개(−166)** 로 정리됐습니다. 이물 없는 사진 26장은 빈 TXT 로 확인했습니다(정상 김치 24 + 김치 · 이물 없음 2).

| 핵심 숫자 | 값 |
|---|---:|
| 이미지 · 라벨 | 900장 · 900개 |
| BBox (원본 → 최종) | 4,399 → **4,405** |
| 그대로 유지 / 위치 · 크기 수정 / Class 변경 / 삭제 / 추가 | 2,016 / 2,014 / 25 / 344 / 350 |
| 사람 검수 완료 (REVIEWED) | **900 / 900** |
| 자동 검사 CRITICAL · 남은 확인 필요(REVIEW) | **0 · 0** |
| 자동 테스트 | 4개 통과 |

## 2. 아키텍처

> 준비 중 — `docs/00_architecture.md` 로 추가합니다.

지금은 이 흐름만 기억하면 됩니다: **원본(RAW, 읽기만) → 작업본(WORK, 프로그램이 저장) → 합치기 · 검수 → FINAL(교과 8 입력)**

## 3. 데이터 분석

- **출처** — 학습데이터1 train 500 · 학습데이터2 train 220 · 학습데이터2 validation 180
- **장면 유형** — 김치 + 이물 725 · 이물만 149 · 정상 김치 24 · 김치 · 이물 없음 2
- **검수 단계** — 1차 라벨링 900장 → 교차검수 710장(수정 · 확인 필요 사진을 다른 사람이 확인) → 최종검수 900장(3명 × 300장, 본인이 검수한 사진 제외) → FINAL

**Class 별 BBox** (원본 → 최종)

| Class | 이름 | 원본 | 최종 | 변화 |
|---:|---|---:|---:|---:|
| 0 | 나뭇잎 · 종이류 | 716 | 709 | −7 |
| 1 | 플라스틱 · 돌 · 금속 | 1,831 | 1,665 | −166 |
| 2 | 나뭇가지류 | 911 | 937 | +26 |
| 3 | 벌레류 | 379 | 378 | −1 |
| 4 | 고무장갑 (사용 안 함 · 배경) | 0 | 0 | 0 |
| 5 | 병해 · 갈변 | 313 | 465 | **+152** |
| 6 | 파 · 고추 | 249 | 251 | +2 |
| | 합계 | 4,399 | 4,405 | +6 |

자세한 숫자 → [reports/01_qa_summary.md](reports/01_qa_summary.md)

## 4. 역할표

| 직책 | 브랜치 | 맡은 일 | 주요 산출물 |
|---|---|---|---|
| PM · Integrator | feature/pm | 일정 · 배분 · Git 관리 · FINAL 생성 | README · Baseline · FINAL · 사용설명서 |
| GUI · Image | feature/gui | 화면 디자인(v01 → v02) · 캡처 · Figma | 프로그램 화면 (`src/ui`) |
| Coord (BBox · Coordinate) | feature/coord | 좌표 · Golden Test · 기준서 | Class 기준서 · BBox 기준서 |
| Storage (Label · Storage) | feature/storage | 저장 로직 · 데이터 취합 · 배포 | 저장 · 병합 (`src/yolo`, `04_merge`) |
| QA (Validation) | feature/qa | 자동 검사 · RAW 보호 · 테스트 | Validation · Test Report |
| Manifest (Document · 서기) | feature/manifest | 작업 장부 · 기록 · 인계 | Manifest · QA Summary · Handoff · 작업 기록 |

## 5. WBS (일정)

| 단계 | 기간 | 한 일 | 결과 |
|---|---|---|---|
| 1 준비 | 10/01 – 10/02 | 조 편성 · 데이터 확인 · 기준 · 환경 · Git | 일정 · 기준 확정 |
| 2 프로그램 | 10/02 – 10/08 | v01 → v02 디자인 → v2.1 · v2.2 | 팀 배포 (Tags v2.1 · v2.2) |
| 3 기준서 | 10/06 – 10/14 | Class v1.0 → v1.7.2 · BBox v1.0 → v1.2 | 판단 기준 통일 |
| 4 1차 라벨링 | 10/06 – 10/07 | 900장 담당별 검수 | 900장 완료 |
| 5 교차검수 | 10/08 – 10/12 | 수정 · 확인 필요 710장 | 다른 사람이 재확인 |
| 6 최종검수 | 10/12 – 10/13 | 3명 × 300장 | 900장 REVIEWED |
| 7 QA · FINAL | 10/13 – 10/15 | Validation · QA Summary · 예외 2장 정리 | CRITICAL 0 · FINAL 900쌍 |
| 8 인계 · 문서 | 10/13 – 10/21 | Handoff · 문서 정리 · 발표 준비 | 교과 8 전달 |

Feature Freeze 10/13 (이후 버그 수정 · 문서만) · 발표 10/21

## 6. 산출물

**필수 산출물 (강사님 11개)**

| 번호 | 산출물 | 위치 | 상태 |
|---:|---|---|---|
| 1 | 라벨링 프로그램 | `main.py` · `src/` | ✅ v2.2 |
| 2 | 소스코드 · 실행 환경 | `src/` · `requirements.txt` · `configs/classes.yaml` | ✅ |
| 3 | FINAL YOLO 라벨 | `data/final/` (사진은 Git 제외) | ✅ 900쌍 |
| 4 | Project Baseline | [docs/01_project_baseline.md](docs/01_project_baseline.md) | ✅ |
| 5 | Class 기준서 | [docs/02_class_guide.md](docs/02_class_guide.md) | ✅ v1.7.2 |
| 6 | BBox 기준서 | [docs/03_bbox_guide.md](docs/03_bbox_guide.md) | ✅ v1.2 |
| 7 | Dataset Manifest | `manifests/dataset_manifest.csv` | ⏳ FINAL 후 생성 |
| 8 | QA Summary | [reports/01_qa_summary.md](reports/01_qa_summary.md) | ✅ |
| 9 | Test Report | [reports/02_test_report.md](reports/02_test_report.md) | ⏳ Golden 결과 칸 채우기 |
| 10 | README | 이 문서 | ✅ |
| 11 | 교과 8 Handoff | [docs/10_subject08_handoff.md](docs/10_subject08_handoff.md) | ✅ |

**우리가 추가한 산출물 (왜 만들었나)**

| 산출물 | 위치 | 추가한 이유 |
|---|---|---|
| 사용설명서 | [docs/04_user_manual.md](docs/04_user_manual.md) | README 는 요약만 두고, 설치 · 실행 · 단축키는 따로 모아 처음 쓰는 사람도 따라 하게 |
| 이슈 → 개선 보고서 | [docs/05_issue_improvement.md](docs/05_issue_improvement.md) | 문제를 어떻게 찾고 고쳤는지 한곳에서 보여 주려고 |
| 버전 기록 | [docs/06_version_history.md](docs/06_version_history.md) | 프로그램 · 기준서 · 데이터가 언제 왜 바뀌었는지 추적 |
| 팀 작업 기록 | [docs/07_team_worklog.md](docs/07_team_worklog.md) | 날짜별로 무엇을 했는지 (서기) |
| 코드 리뷰 | [docs/08_code_review.md](docs/08_code_review.md) | 핵심 파일을 의사코드 · 흐름도로 설명 (교과 2 코드리뷰 방식) |
| 코드 공부 자료 | [docs/09_code_study.md](docs/09_code_study.md) | 팀원 모두가 코드를 설명할 수 있게 |
| 자동 검사 결과 | `reports/03_validation_final.csv` | CRITICAL 0 을 파일로 증명 |
| 작업 장부 사본 | `manifests/manifest_final.csv` | 900장 상태 · 검수자 · 장면 유형 기록 |
| 화면 이미지 | `docs/images/` | 프로그램 작동 · 디자인 변화(v01 → v02) · BBox 예시 |

## 7. 폴더 구조 (담당 · 마지막 수정일)

| 위치 | 무엇 | 담당 | 수정일 |
|---|---|---|---|
| `README.md` | 이 문서 (요약) | PM | 10/15 |
| `main.py` · `run.sh` · `setup_wsl.sh` | 실행 · 설치 | PM | 10/12 |
| `requirements.txt` · `settings.example.json` | 실행 환경 · 설정 예시 | PM | 10/12 |
| `configs/classes.yaml` | Class 0~6 이름 · 색 | Storage | 10/12 |
| `src/ui/` | 화면 · 메뉴 · 한글 입력 | GUI | 10/15 |
| `src/bbox/` | BBox 그리기 · 좌표 · 저장 규칙 | Coord | 10/12 |
| `src/yolo/` | YOLO TXT 읽기 · 쓰기 · FINAL 이름 | Storage | 10/12 |
| `src/validation/` | 자동 검사 · 통계 | QA | 10/13 |
| `src/manifest*.py` · `src/config.py` | 작업 장부 · 기준 설정 | Manifest · PM | 10/12 |
| `scripts/00~10` | 운영 스크립트 (RAW 확인 → FINAL → 인계) | PM · QA · Storage · Manifest | 10/15 |
| `tests/test_core.py` | 자동 테스트 4개 | QA | 10/12 |
| `docs/00~10` | 기준서 · 설명서 · 기록 · 인계 (아래 문서 지도) | 문서마다 표시 | 10/15 |
| `docs/images/` | 작동 화면 · 디자인 v01 · v02 · BBox 예시 | GUI · Coord | 10/15 |
| `manifests/` | 작업 장부 사본 (+ 제출 Manifest 예정) | Manifest | 10/14 |
| `reports/01~03` | QA Summary · Test Report · 검사 결과 | Manifest · QA | 10/15 |

## 8. 문서 지도 — 무엇을 보려면 어디로

| 알고 싶은 것 | 볼 문서 | 다음에 볼 문서 |
|---|---|---|
| 프로젝트 기준 · 완료 조건 | [01 Project Baseline](docs/01_project_baseline.md) | 02 Class 기준서 |
| 어떤 Class 로 라벨할지 | [02 Class 기준서](docs/02_class_guide.md) | 03 BBox 기준서 |
| 박스를 어디까지 그릴지 | [03 BBox 기준서](docs/03_bbox_guide.md) | 04 사용설명서 |
| 설치 · 실행 · 단축키 | [04 사용설명서](docs/04_user_manual.md) | 05 이슈 보고서 |
| 어떤 문제가 있었고 어떻게 고쳤나 | [05 이슈 → 개선](docs/05_issue_improvement.md) | 06 버전 기록 |
| 언제 무엇이 바뀌었나 | [06 버전 기록](docs/06_version_history.md) | 07 작업 기록 |
| 날짜별 팀 작업 | [07 팀 작업 기록](docs/07_team_worklog.md) | 08 코드 리뷰 |
| 코드가 어떻게 동작하나 | [08 코드 리뷰](docs/08_code_review.md) → [09 코드 공부](docs/09_code_study.md) | 10 인계 |
| 교과 8 에 무엇을 넘기나 | [10 교과 8 Handoff](docs/10_subject08_handoff.md) | reports |
| 검수 결과 숫자 | [reports/01 QA Summary](reports/01_qa_summary.md) | 02 Test Report |

**오류가 나면 어디를 보나**

| 증상 | 먼저 볼 곳 |
|---|---|
| 설치 · 실행이 안 됨 | 04 사용설명서 «8. 문제 해결» |
| 저장이 안 되거나 박스가 이상함 | 04 사용설명서 «4. 저장 규칙» → 08 코드 리뷰 |
| Validation 에 CRITICAL 이 뜸 | reports/03_validation_final.csv → 02 Class 기준서 |
| QA Summary 숫자가 0 으로 나옴 | 05 이슈 보고서 ISSUE-07 (경로 문제) |
| Class 판단이 애매함 | 02 Class 기준서 «헷갈리기 쉬운 Class 구분표» |

## 9. 버전 · 이슈

- 지금 버전: 프로그램 **v2.2** · Class 기준서 **v1.7.2** · BBox 기준서 **v1.2** · 데이터 **FINAL 900** → [06 버전 기록](docs/06_version_history.md)
- 주요 이슈와 개선 · 고도화 계획 → [05 이슈 → 개선](docs/05_issue_improvement.md)

## 10. 보안 · 주의

- 데이터는 AI캠퍼스 교육용 **100% 가상 생성** 데이터이며 **NDA 대상**입니다.
- **원본 김치 사진은 Git · 메신저 · 개인 클라우드 금지** (메일 · USB 로만). 라벨 TXT · CSV 는 Git 허용 (10/13 강사님 확인).
- RAW 는 수정하지 않습니다. 고칠 때는 WORK 에서 고친 뒤 FINAL 을 다시 만듭니다.
- main 은 PR 로만 바꿉니다. `git add .` 금지.
