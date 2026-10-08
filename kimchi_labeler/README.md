# 조각김치 이물검출 라벨링 프로그램 (교과 7)

기존 YOLO TXT 를 불러와서 사람이 검수하고, 필요한 라벨만 보정한 뒤, 교과 8 에서 바로 학습할 수 있는 **FINAL 데이터**를 만드는 팀 프로젝트용 프로그램입니다.

> 본 프로젝트는 AI캠퍼스 교육을 위해 실제 산업데이터와 유사한 분포 구조로 **100% 가상 생성된** 조각김치 이물검출 학습데이터를 활용하여 수행하였습니다.
> 데이터는 **NDA 대상**입니다. JPG·TXT·WORK·FINAL 폴더를 Git, 메신저, 개인 클라우드에 올리지 않습니다.

---

## 1. 설치 (WSL, 처음 한 번)

전제: Windows 11 + WSL2(Ubuntu 22.04 이상). 아래는 모두 **WSL 터미널**에서 실행합니다.

```bash
# 1) GitHub 에서 받기 (폴더 이름은 group2_project 로 통일)
git clone https://github.com/sunghyunglee6334-web/group2-project.git ~/group2_project

# 2) 설치 (패키지, 한글 글꼴, 가상환경, 연습 데이터, 자동 테스트)
cd ~/group2_project/kimchi_labeler
bash setup_wsl.sh
```

마지막에 `모든 테스트 통과 (4개)` 와 `설치 완료.` 가 나오면 준비 끝입니다.
창 제목줄의 한글이 네모로 보이면 **Windows PowerShell** 에서 `wsl --shutdown` 을 한 번 실행하고 WSL 을 다시 여세요.

## 2. 실행

```bash
cd ~/group2_project/kimchi_labeler
bash run.sh --raw data/dummy_raw     # 처음: 연습 데이터로 실행 (폴더는 기억됨)
bash run.sh                          # 다음부터
```

- 처음 실행하면 **작업자 이름**을 물어봅니다. 한 번 입력하면 기억합니다.
- 실제 데이터로 바꿀 때: 메뉴 **파일 → RAW 폴더 열기** (Ctrl+O) 에서 `이물검출_학습데이터1`, `이물검출_학습데이터2` 가 **바로 안에 들어 있는 폴더**를 고르세요.
- RAW 와 WORK 가 겹치면 프로그램이 실행을 거부합니다.

## 3. 새 버전으로 업데이트

```bash
cd ~/group2_project
git switch main && git pull origin main
```

- 코드만 새 버전으로 바뀝니다. 내 작업(`data/`, `settings.json`, `.venv`)은 `.gitignore` 대상이라 그대로 남습니다.
- 버전 기록은 GitHub 의 **Tags** (v2.1, v2.2 …) 에서 확인합니다.

## 4. 설정 파일 (settings.json)

프로그램이 자동으로 만들고 기억합니다. 직접 고칠 때만 참고하세요. (`settings.json` 은 Git 에 올리지 않습니다)

```json
{
  "raw_root":  "/home/<이름>/kimchi_labeler/data/raw",
  "work_root": "/home/<이름>/kimchi_labeler/data/work",
  "worker": "홍길동"
}
```

- `raw_root` : 원본 폴더. **절대 수정하지 않습니다.**
- `work_root` : 수정한 라벨(`labels/`)과 `manifest.csv` 가 저장되는 곳

### 화면 구성

토스 앱처럼 연한 회색 바탕 위에 둥근 흰 카드로 나뉘어 있습니다.

```text
 조각김치 라벨링 ⌄   (상태 메시지)                          [폴더 열기] [파일 열기] [Validation] [⋯]
 ┌ 작업 현황 ────┐ ┌ 파일명                  ● 저장 안 됨 ┐ ┌ Class ────────────┐
 │ 3 / 900장 완료 │ │ 출처 · 크기 · 라벨 출처        배율 / 좌표 │ │ ⓪ 나뭇잎·종이류   1개 │
 │ ▬ 상태별 막대   │ │ ⚠ 경고 (있을 때만)                     │ └───────────────────┘
 └──────────────┘ │            이미지 + BBox     [미니맵]   │ ┌ 선택한 BBox ───────┐
 ┌ 전체|내 담당|확인 필요 ┐   ( −  50%  + │ 맞춤  100% )     │ │ X  Y  너비  높이 [좌표 적용] │
 │ ✓ 파일명    PASS │ │ [그리기][박스 편집][화면 이동] ‹ 3/900 › [라벨 숨김][되돌리기][삭제] │ │ BBox 목록  │
 └─────────────────┘ └───────────────────────────────────────┘ └───────────────────┘
                                                                ┌ 검수 상태 ─────────┐
                                                                │ PASS 수정 확인필요 검수완료 │
                                                                │ 장면 유형 · 작업자 · 검수자 │
                                                                │ 작업자 · 검수자        │
                                                                └───────────────────┘
                                                                ┌ 이슈 · 노트 [영문/한글] ┐
                                                                │ 이슈  문제            │
                                                                │ 노트  판단 · 수정 이유  │
                                                                └───────────────────┘
                                                                [ 저장 ][ 저장하고 다음 (→) ]
```

| 위치 | 내용 |
|---|---|
| 맨 위 | **조각김치 라벨링 ⌄** (파일 메뉴), 상태 메시지, **폴더 열기** (RAW 폴더), **파일 열기** (연습용 이미지 추가), **Validation**, **⋯** (보기·도구·검수·통계·도움말 메뉴) |
| 왼쪽 위 | **작업 현황**: 전체 진행 장수와 상태별 막대 (PASS / 수정 / 확인 필요 / 검수 완료 / 대기) |
| 왼쪽 아래 | **이미지 목록**: 탭(전체 / 내 담당 / 확인 필요), 동그라미 = 상태 (✓ PASS·검수 완료, 연필 = 수정, ! = 확인 필요, 빈 회색 = 대기), 오른쪽 = 상태 글자. 파일명이 길면 … 로 줄여서 겹치지 않음. 클릭하면 이동. 다른 필터는 ⋯ → 보기 → 목록 보기 필터 |
| 가운데 | 파일명, 출처·크기·라벨 출처, 저장 상태, 배율·마우스 좌표, 경고, 이미지와 BBox, **Zoom 막대**, 확대 시 **미니맵**, 아래쪽 모드·이동·라벨 숨김·Undo·삭제 |
| 오른쪽 | **Class** (누르면 선택, 오른쪽 숫자 = 이 이미지의 Class 별 BBox 개수), **선택한 BBox** YOLO 좌표 (고치고 Enter 또는 [좌표 적용]), **BBox 목록**, **검수 상태** (PASS 파랑 / 수정=EDITED 주황 / 확인 필요=REVIEW 빨강 / 검수 완료=REVIEWED 초록), 장면 유형(눌러서 선택), **작업자/검수자**, 파일 정보, **이슈 · 노트** |
| 오른쪽 아래 | **저장** / **저장하고 다음 (→)** |

### 편집 모드 (이미지 아래 버튼)

| 버튼 | 하는 일 |
|---|---|
| **그리기** (`W`) | 빈 곳을 드래그하면 새 BBox, 클릭하면 BBox 선택 |
| **박스 편집** (`V`) | BBox 를 골라 옮기거나 흰 핸들로 크기 조절. 이미지는 움직이지 않음 |
| **화면 이동** | 드래그하면 보는 위치만 이동. BBox 는 바뀌지 않음. 한 번 더 누르거나 `Esc` 면 그리기로 돌아감 |

### 확대 / 축소

- 이미지 아래 가운데 막대: `−` / 배율 / `+` / **맞춤** / **100%**
- `+` `-` 는 25 → 33 → 50 → 67 → 75 → 100 → 125 → 150 → 200% 처럼 한 단계씩, 바뀐 배율이 화면 가운데에 잠깐 크게 표시됩니다.
- 이미지가 화면보다 커지면 오른쪽 아래에 **미니맵**이 나옵니다. 파란 사각형이 지금 보는 영역이고, 누르거나 끌면 그 위치로 이동합니다.

### 한글 입력 (이슈 · 노트 · 작업자 · 검수자 칸)

WSL 로 띄운 창에는 Windows 한글 입력기가 전달되지 않아서, 프로그램 안에 **두벌식 한글 입력기**를 넣었습니다.

- `Shift+Space`, `한/영` 키, 또는 이슈 · 노트 오른쪽 **[영문]** 버튼 → **[한글]** (파란색) 이면 한글 입력
- Windows 에서 직접 실행해서 원래 한글 입력기가 되는 PC 는 [영문] 상태로 두고 원래 입력기를 써도 됩니다.

### 마우스와 단축키

| 조작 | 기능 |
|---|---|
| `W` 새 BBox 모드에서 왼쪽 드래그 | 새 BBox (현재 선택된 Class). 클릭만 하면 BBox 선택 |
| `V` 선택 이동 모드에서 BBox 드래그 | BBox **이동** |
| 선택된 BBox 의 흰 사각 핸들 드래그 | BBox **크기 조절** (모서리·변 8곳) |
| 오른쪽 BBox 정보 칸에 숫자 입력 후 Enter | YOLO 좌표로 정밀 수정 |
| 오른쪽/가운데 드래그, 또는 Pan 모드 | 화면 이동 |
| 마우스 휠 | 마우스 위치 기준 Zoom |
| `0`~`6` | Class 선택 / 선택 BBox 의 Class 변경 (4 는 사용 불가) |
| `Del` / `Ctrl+Z` / `Esc` | 삭제 / Undo / 선택 해제 (화면 이동 중이면 그리기로 돌아감) |
| `A` `←` `↑` / `D` `→` `↓` / `N` | 이전 / 다음 / 다음 미완료 이미지 |
| `Space` / `Ctrl+S` | 저장 후 다음 / 저장 |
| `F` / `+` / `-` / `H` | Fit / Zoom In / Zoom Out / 라벨 숨기기·보이기 |
| `한/영` 또는 `Shift+Space` | 한/영 전환 (메모 입력) |
| `P` / `E` / `R` | PASS / EDITED / REVIEW |
| `Ctrl+O` / `Ctrl+Q` / `F1` | 폴더 열기 / 종료 / 단축키 보기 |
| `Alt+F` `Alt+V` `Alt+T` `Alt+Q` `Alt+S` `Alt+H` / `F10` | 메뉴 열기 (열린 뒤 방향키·Enter·Esc). 마우스로는 맨 위 '조각김치 라벨링 ⌄' 와 '⋯' |

### 메뉴 주요 기능

- **파일**: 폴더 열기 (RAW 폴더), 파일 열기 (연습용 이미지 추가, 실제 RAW 에서는 막힘), 저장, 종료
- **보기**: Fit/Zoom, 라벨 숨기기, 목록 필터 (내 담당, 내 검수 대상, REVIEW, EDITED, Pilot, PASS 표본검수 등)
- **도구**: 모드 전환, 삭제, Undo, **Validation** (결과 행을 더블클릭하면 그 이미지로 이동)
- **검수**: 상태 지정, 다음 미완료 이미지, 검수용 필터 바로가기
- **통계**: 진행현황 (상태·담당자·Scene Type·Dataset), Class 별 BBox 통계, QA Summary 생성

### 저장 규칙 (프로그램이 자동으로 지킴)

- 저장은 항상 WORK 에만 합니다. RAW 는 열기만 합니다.
- 라벨을 바꾸고 PASS 를 누르면 자동으로 **EDITED** 로 저장됩니다.
- 라벨을 안 바꿨으면 RAW TXT 를 **바이트 그대로** WORK 에 복사합니다.
- 저장하지 않고 이동하거나 창을 닫으면 (터미널 `Ctrl+C` 포함) 저장 여부를 묻습니다.
- Class 4 가 남아 있으면 PASS 나 REVIEWED 대신 **REVIEW** 로 저장합니다.
- 자기 작업을 REVIEWED 로 바꾸려 하면 경고합니다. 교차검수는 다른 사람이 합니다.
- TXT 는 임시파일에 쓴 뒤 교체하는 방식이라, 저장 도중 꺼져도 깨지지 않습니다.

## 5. 스크립트 (프로젝트 루트에서 실행)

| 순서 | 명령 | 언제 / 누가 |
|---|---|---|
| 0 | `python scripts/00_raw_snapshot.py` | 처음 1번 (PM). RAW 해시 기록 |
| 0 | `python scripts/00_raw_snapshot.py --verify` | 매일 마감 (QA). RAW 가 그대로인지 확인 |
| 1 | `python scripts/01_build_manifest.py` | 처음 1번 (Data). Manifest + Data Inventory |
| 2 | `python scripts/02_validate.py --target raw` | 처음 1번 (QA). 원본 위험 이미지 목록 |
| 2 | `python scripts/02_validate.py` | 매일 마감 (QA). WORK 기준 검사 |
| 3 | `python scripts/03_assign.py --workers A B C D E F --pilot 30` | 배분 (PM) |
| 4 | `python scripts/04_merge.py --inputs ... --out ...` | 매일 마감 (Data). 팀원 WORK 병합 |
| 5 | `python scripts/05_qa_summary.py` | 매일 마감 (Doc). `reports/qa_summary.md` |
| 6 | `python scripts/06_pass_sample.py --ratio 0.25` | 4일차 (QA). PASS 표본 선정 |
| 7 | `python scripts/07_build_final.py` | 마지막 날 (PM). 조건 통과 시에만 FINAL 생성 |
| 8 | `python scripts/08_handoff.py` | 마지막 날 (Doc). `docs/subject08_handoff.md` |
| 9 | `python scripts/09_golden_test.py --n 20` | 기능 바꿀 때마다 (QA). Golden Sample 시험 |
| 10 | `python scripts/10_export_manifest.py` | 매일 마감·마지막 날 (Data). `manifests/dataset_manifest.csv` |
| - | `python scripts/make_dummy_data.py` | 연습용 가짜 데이터 (NDA 데이터 없이 개발할 때) |

## 6. 폴더 구조와 산출물 위치

```text
kimchi_labeler/
├── main.py                       실행 진입점
├── setup_wsl.sh                  WSL 처음 설치 (bash setup_wsl.sh)
├── run.sh                        실행 (bash run.sh)
├── requirements.txt              실행 환경
├── README.md                     ← 산출물 10
├── settings.example.json         설정 예시 (settings.json 은 각자 PC 에만)
├── configs/
│   └── classes.yaml              ← 산출물 2  Class 0~6 이름·사용 여부·색 (프로그램이 읽음)
├── src/                          ← 산출물 1·2
│   ├── config.py                 경로·상태 기준, classes.yaml 읽기
│   ├── manifest.py               작업 Manifest CSV 읽기/쓰기/병합
│   ├── manifest_builder.py       RAW → Manifest 행 생성
│   ├── ui/                       Tkinter 화면
│   │   ├── app.py                메인 창: 메뉴·단축키·이미지 이동·저장
│   │   ├── panels.py             위젯 배치 (토스 스타일 카드 레이아웃)
│   │   ├── widgets.py            둥근 카드·버튼, 탭, 카드형 목록, 막대 그래프
│   │   ├── overlay.py            이미지 위 Zoom 막대 · 미니맵 · 배율 표시
│   │   ├── hangul.py             내장 두벌식 한글 입력기 (WSL 한글 입력)
│   │   ├── menubar.py            메뉴 (WSLg 잔상 해결, 버튼 아래에 열림)
│   │   ├── dialogs.py            Validation·진행현황·통계·도움말·이름 입력 창
│   │   └── style.py              색·글꼴(한글 글꼴 자동 선택)
│   ├── bbox/                     BBox 편집
│   │   ├── canvas_editor.py      이미지·BBox 그리기, 마우스로 추가/이동/크기조절
│   │   ├── view.py               화면↔원본 좌표 변환, Zoom/Pan
│   │   └── session.py            BBox 편집·Undo·저장 핵심 로직 (GUI 없이 테스트 가능)
│   ├── yolo/                     YOLO 데이터
│   │   ├── yolo_io.py            YOLO TXT 읽기/쓰기, YOLO↔픽셀 변환, 안전저장
│   │   ├── dataset.py            RAW 구조 조사 (Dataset/split 출처 보존)
│   │   └── final_layout.py       FINAL images/ · labels/ 파일 이름 규칙
│   └── validation/               검사
│       ├── validator.py          자동 Validation
│       └── stats.py              QA 통계 (추가/삭제/Class변경 계산)
├── scripts/                      00~10 운영 스크립트
├── tests/test_core.py            자동 테스트 (전체 작업 흐름 시뮬레이션)
├── docs/
│   ├── project_baseline.md       ← 산출물 4
│   ├── class_guide.md            ← 산출물 5
│   ├── bbox_guide.md             ← 산출물 6 (예시 이미지: docs/images/)
│   ├── subject08_handoff.md      ← 산출물 11 (08_handoff.py 가 작성)
│   ├── CODE_GUIDE.md             코드 설명 (역할별)
│   ├── STUDY_GUIDE.md            코드 분석 공부 자료
│   └── team/                     팀 실행 가이드·공부 자료·PM 계획 PDF
├── manifests/
│   └── dataset_manifest.csv      ← 산출물 7 (10_export_manifest.py 가 작성)
└── reports/
    ├── qa_summary.md             ← 산출물 8 (05_qa_summary.py 가 작성)
    ├── test_report.md            ← 산출물 9
    └── golden_test.txt           Golden 시험 결과 (09_golden_test.py)
```

데이터 (Git 제외, NDA)

```text
data/raw/      원본 RAW: 이물검출_학습데이터1/images|labels/train, 이물검출_학습데이터2/images|labels/train|validation
data/work/          작업 중: manifest.csv, raw_checksums.csv, labels/<RAW 와 같은 구조>
data/final/             ← 산출물 3: images/ 900장, labels/ 900개 (같은 파일명 Pair)
                        + manifest_final.csv, final_file_map.csv(원래 Dataset/split), FINAL_INFO.json
data/dummy_raw/         연습용 가상 데이터
```

| 산출물 | 위치 | 만드는 방법 |
|---|---|---|
| 1 라벨링 프로그램 | `main.py`, `src/` | `bash run.sh` |
| 2 소스코드 | `src/`, `requirements.txt`, `configs/classes.yaml`, Git 이력 | `git log --oneline --graph --all > git_commit_history.txt` |
| 3 FINAL YOLO 라벨 | `data/final/images`, `data/final/labels` | `python scripts/07_build_final.py` |
| 4 Project Baseline | `docs/project_baseline.md` | 직접 작성 |
| 5 Class 기준서 | `docs/class_guide.md` | 직접 작성 |
| 6 BBox 기준서 | `docs/bbox_guide.md` | 직접 작성 |
| 7 Dataset Manifest | `manifests/dataset_manifest.csv` | `python scripts/10_export_manifest.py` |
| 8 QA Summary | `reports/qa_summary.md` | `python scripts/05_qa_summary.py` 후 다듬기 |
| 9 Test Report | `reports/test_report.md` | Golden·Pilot·Acceptance 결과 기록 |
| 10 README | `README.md` | 이 문서 |
| 11 교과 8 Handoff | `docs/subject08_handoff.md` | `python scripts/08_handoff.py` 후 다듬기 |

## 7. Class ID (Freeze, 다시 번호 매기기 금지)

Class 이름·사용 여부·화면 색은 `configs/classes.yaml` 에서 관리합니다. 상세 판단 기준은 `docs/class_guide.md`.

| ID | 이름 | 사용 |
|---:|---|---|
| 0 | 나뭇잎·종이류 | O |
| 1 | 플라스틱·돌·금속 | O |
| 2 | 나뭇가지류 | O |
| 3 | 벌레류 | O |
| 4 | 고무장갑 | **X (발견하면 삭제하지 말고 REVIEW)** |
| 5 | 병해·갈변 | O |
| 6 | 파·고추 | O |

## 8. 알려진 제한

- 여러 PC 에서 동시에 작업한 결과는 하루 마감 때 `04_merge.py` 로 합칩니다. 같은 이미지는 담당자만 수정합니다.
- 짝 없는 TXT(PAIR_NO_JPG)는 프로그램에서 고칠 수 없으니 강사나 담당자에게 보고합니다.
- 프로그램 실행 중에는 `manifest.csv` 를 엑셀로 열어 두지 마세요. Windows 에서 파일이 잠겨 저장이 실패합니다 (실패하면 프로그램이 알려주고 이동하지 않습니다).
