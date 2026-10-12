# Labeling Tool Test Report

기능 검증은 **기능 확인 → Golden Test → Pilot Test → 전체 Validation → Acceptance Test** 순서로 넓혀 갑니다.
실패는 `문제 → 원인 → 조치 → 재시험` 네 줄로 기록합니다.

---

## 0. 개발 단계에서 발견·수정한 오류

실제 데이터 작업 전에 WSL 환경에서 프로그램을 시험하면서 찾은 오류입니다.

| 번호 | 문제 | 원인 | 조치 | 재시험 |
|---|---|---|---|---|
| DEV-01 | 메뉴를 열고 다른 메뉴로 옮기면 이전 드롭다운이 화면에 남음 | WSLg 가 tk.Menu 의 별도 드롭다운 창이 닫힌 자리를 다시 그리지 않음 | 메뉴를 메인 창 안의 Frame 으로 직접 구현 (`gui/menubar.py`) | PASS |
| DEV-02 | 메뉴 위에 마우스를 올렸다 빠르게 나가면 메뉴 제목 색이 남음 | WSLg 에서 `<Leave>` 이벤트가 오지 않는 경우가 있음 | hover 색을 없애고 열린 메뉴만 칠함 | PASS |
| DEV-03 | 옆 메뉴로 옮겨 열린 메뉴를 바로 클릭하면 닫혀 버림 | 클릭을 '같은 메뉴 다시 누름'으로 처리 | hover 로 막 열린 메뉴는 클릭해도 유지 | PASS |
| DEV-04 | 메뉴를 닫으려고 이미지 목록을 누르면 이미지가 바뀜 | 바깥 클릭이 아래 위젯에도 전달됨 | 메뉴가 열려 있을 때 첫 바깥 클릭은 메뉴 닫기에만 사용 | PASS |
| DEV-05 | Caps Lock 이 켜져 있으면 Ctrl+S 저장이 안 됨 | 대문자 `<Control-S>` 를 묶지 않음 | 대·소문자 모두 바인딩 | PASS |
| DEV-06 | 필터 결과가 0장이면 이전 이미지의 경고·정보가 남음 | 빈 화면에서 정보 칸을 비우지 않음 | `show_empty_view()` 에서 모두 초기화 | PASS |
| DEV-07 | 깨진 이미지를 열면 이전 사진 위에 새 BBox 가 겹쳐 보임 | 불러오기 실패 시 이전 이미지 피라미드가 남음 | 실패 시 화면을 비우고 편집 불가 상태로 표시 | PASS |
| DEV-08 | `--raw` 로 실행하면 WORK 폴더 이름이 폴더 선택과 달라짐 | 명령줄 경로는 settings 의 work_root 를 그대로 사용 | 두 경우 모두 `data/work_<RAW폴더이름>` 으로 통일 | PASS |

---

## 1. Golden Test

### 테스트 목적
900장 작업을 시작하기 전에 핵심 기능이 정상인지 소수의 실제 데이터로 확인합니다.

### 테스트 데이터
- 실제 조각김치 이미지: (  )장, 목록 `golden.txt`
- 자동 시험: `python scripts/09_golden_test.py --list golden.txt` → `reports/golden_test.txt`

### 테스트 결과

| 테스트 항목 | 결과 |
|---|---|
| 이미지 열기 | |
| 기존 YOLO TXT Load (TXT 줄 수 = 화면 BBox 수) | |
| 기존 BBox 표시 | |
| BBox 추가 | |
| BBox 수정 (이동·크기 조절·좌표 입력) | |
| BBox 삭제 | |
| Class 변경 | |
| Zoom | |
| Pan | |
| YOLO TXT 저장 | |
| 저장 후 Reload (좌표 왕복 오차 < 1e-6) | |
| 수정 없이 저장 = RAW 와 바이트 동일 | |
| Validation | |

최종 결과: (  ) / (  ) PASS

---

## 2. Pilot Test

### 테스트 목적
실제 900장 작업을 시작하기 전에 작업 흐름 전체(배분 → 작업 → 병합 → 교차검수)가 안정적인지 확인합니다.

### 테스트 데이터
- 실제 이미지 30장 (`03_assign.py --pilot 30`, 1인 5장)

### 최초 결과
- PASS: (  )장
- FAIL: (  )장
- 1장 평균 처리 시간: (  )분

### 발견된 문제

#### FAIL-01
문제:
원인:
조치:
재시험:

### Pilot 최종 결과
- PASS: (  )장
- FAIL: 0장

---

## 3. Final Acceptance Test

### 테스트 목적
900장 검수가 끝난 뒤 프로그램과 FINAL 데이터가 최종 사용 가능한 상태인지 확인합니다.
만든 사람이 아닌 팀원이 README 만 보고 진행합니다.

### 확인 항목

| 항목 | 결과 |
|---|---|
| 900장 이미지 탐색 가능 | |
| 이미지와 TXT Pair 정상 (images 900 / labels 900) | |
| 저장 후 Reload 정상 | |
| 미처리 REVIEW 0 | |
| Critical Error 0 | |
| Validation 오류 0 (`02_validate.py`) | |
| RAW 변경 0 (`00_raw_snapshot.py --verify`) | |
| `07_build_final.py` 성공 | |

### 최종 결과
- 전체 대상: 900장
- Critical Error: (  )건
- Unresolved Review: (  )건
- Validation Error: (  )건

최종 판정: (ACCEPTED / 보류)
