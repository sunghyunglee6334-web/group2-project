# group2-project — 조각김치 이물검출 AI

## 프로젝트 소개

### 개요

조각김치 이물검출 · 2조 팀 프로젝트입니다. 제공된 원본 라벨에는 오표기 · 누락이 많아 그대로 학습할 수 없었습니다. 그래서 **교과 7** 에서 라벨링 프로그램을 직접 만들어 900장을 전수 검수해 **정답 데이터(FINAL 900쌍)** 를 만들고, **교과 8** 에서 그 데이터로 **YOLO11** 을 학습 · 개선 · 검증한 뒤 **Auto Label** 로 다시 교과 7 프로그램에 연결했습니다.

목표는 높은 점수가 아니라 **신뢰할 수 있는 데이터**입니다. 검수 조건을 모두 통과한 라벨만 FINAL 로 만들고, 같은 촬영 묶음이 학습과 평가에 섞이지 않게 나누고, Final Model 은 **Frozen Test 를 보기 전에** 확정했습니다.

<br>

### 작업 결과

| 구분 | 핵심 결과 |
|---|---|
| 교과 7 · 라벨링 | 900장 **전수 검수** · **778장(86%)** 수정 · BBox 2,383개 수정 · 누락 350개 추가 · CRITICAL **0** |
| 교과 7 · 기준 | 고무장갑은 **배경** 으로 정의 → 실제 이물만 검출 · Class 0 ~ 6 (4번 미사용) |
| 교과 8 · Split | 5분 촬영 묶음 단위 · Train 609 · Val 66 · Test 75 · Bridge 150 · 누수 0 |
| 교과 8 · 모델 | Baseline mAP50-95 **0.345** → Final **EXP003 (yolo11n · 1280) 0.446 (+29%)** |
| 교과 8 · 검증 | Frozen Test 1회 · mAP50-95 **0.4115** |
| 교과 8 · 활용 | Final Model 후보 라벨 → 교과 7 프로그램 **Human Review** 로 확정 |

<br>

### Architecture

원본 RAW 는 읽기만 하고, 검수를 모두 통과한 **FINAL 900쌍** 만 교과 8 로 넘어갑니다. 교과 8 은 묶음 단위로 나누고 **변수 하나씩** 개선해 Final Model 을 고르고, Final Model 이 만든 후보 라벨은 다시 **교과 7 프로그램에서 사람이 확정**합니다.

![조각김치 이물검출 AI Architecture](docs/architecture.svg)

<br>

### 화면 설계 · 작동 화면

교과 7 에서 직접 만든 라벨링 프로그램 **kimchi_labeler** 입니다. 교과 8 의 Final Model 이 만든 후보 라벨도 이 화면에서 **Human Review** 로 확정합니다.

![SCR-01 메인 작업 화면 UI 스토리보드](project7/docs/images/gui_main.png)

*화면 ID SCR-01 · 번호는 화면 영역, 오른쪽 표는 영역별 기능 · 동작 · 단축키입니다. NDA 에 따라 원본 사진은 블러 처리했습니다.* 사용 방법 → [교과 7 사용설명서](project7/docs/04_user_manual.md)

<br>

### 바로가기

| 폴더 | 무엇인가 | 핵심 |
|---|---|---|
| [**project7**](project7/README.md) | **교과 7 · 라벨링** — 라벨링 프로그램 kimchi_labeler 와 900장 검수 · FINAL 데이터 | 정답 데이터 만들기 · Tkinter 프로그램 · Class · BBox 기준서 |
| [**project8**](project8/README.md) | **교과 8 · 객체검출** — YOLO11 학습 · 실패 분석 · 개선 · Frozen Test · Auto Label | 모델 만들기 · Split · 실험 기록 · Final Model |

<br><br>

## 빠른 시작

준비물: Windows 11 PC · 교과 8 학습 · 평가에는 NVIDIA GPU

**1단계 · WSL 설치 (처음 한 번)** — PowerShell 을 **관리자 권한으로 실행**

```powershell
wsl --install
```

**2단계 · 받기** — Ubuntu 창에서

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/sunghyunglee6334-web/group2-project.git ~/group2_project
```

**3단계 · 교과 7 라벨링 프로그램** — 설치 · 테스트 후 연습 데이터로 실행

```bash
cd ~/group2_project/project7
bash setup_wsl.sh
bash run.sh --raw data/dummy_raw
```

**4단계 · 교과 8 객체검출** — 메일 · USB 로 받은 FINAL 900쌍을 `project8/data/final/` 에 넣은 뒤

```bash
cd ~/group2_project/project8
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python scripts/01_check_environment.py
python scripts/03_build_split.py
```

학습된 Weight 는 `project8/models/` 에 함께 받아지므로 다시 학습하지 않아도 평가 · Detection 을 바로 실행할 수 있습니다. 자세한 실행 순서 → [교과 7 빠른 시작](project7/README.md#빠른-시작) · [교과 8 실행방법](project8/README.md#5-실행방법)

<br><br>

## 주의사항

- **원본 김치 사진 · 사진이 보이는 결과 이미지 · 영상은 Git 금지** — 라벨 TXT · CSV · 문서 · 학습 그래프는 허용 (10/13 강사님 확인)
- 데이터는 AI캠퍼스 교육용 **100% 가상 생성** 데이터이며 **NDA 대상**입니다.
- main 은 PR 로만 변경 · `git add .` · `git add -f` 금지 (파일 이름으로만 add)
