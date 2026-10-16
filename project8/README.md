# project8 — 교과 8 조각김치 이물검출 객체검출 (YOLO11n)

> **원본 김치 사진 · 사진이 보이는 결과 이미지 · 영상은 NDA 로 Git 에 올리지 않습니다.** 라벨 TXT · CSV 는 허용 (2026-10-13 강사님 확인) · Weight(.pt) 와 학습용 data/ 는 용량 때문에 제외합니다.

## 1. 프로젝트 목적
교과 7 FINAL 900장으로 YOLO11n 을 학습 · 평가 · 실패분석 · 한 변수 개선 → Final Model · Frozen Test · Detection · Auto Label 까지 완성

## 2. 교과 7 → 교과 8 연결
- 교과 7 라벨링 프로그램 · 산출물: [../project7](../project7)
- 교과 7 FINAL 위치: TBD (10/15 FINAL 확정 후)

## 3. Dataset
- JPG 900 / YOLO TXT 900 · Dataset 1 (train) · Dataset 2 (train · validation)
- scene_type: kimchi_with_target · normal_kimchi · object_only · none · other_review
- Dataset Version: TBD

## 4. Class (교과 7 기준 유지 · 번호 변경 금지)
| ID | 한글 | 영문 |
|---|---|---|
| 0 | 나뭇잎·종이류 | leaf_paper |
| 1 | 플라스틱·돌·금속 | plastic_stone_metal |
| 2 | 나뭇가지류 | branch |
| 3 | 벌레류 | insect |
| 4 | 고무장갑 (미사용) | rubber_glove_unused |
| 5 | 병해·갈변 | disease_browning |
| 6 | 파·고추 | green_onion_pepper |

## 5. 실행환경
- Windows 11 + WSL2 Ubuntu + VS Code
- PyTorch: 2.14.1 · Ultralytics: 8.4.175 (requirements.txt) · Python: TBD (`scripts/01_check_environment.py` 결과)
- GPU: NVIDIA GeForce RTX 3060 12GB · WSL 에서 `torch.cuda.is_available() = True` (팀 PC 전부 같은 사양 · 2026-10-15 확인)
- 환경 확인: `python scripts/01_check_environment.py`
- 설치: `cd project8 && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## 6. Dataset Split (Train · Validation · Frozen Test · Bridge Holdout)
**2026-10-15 Split Freeze (PR #40 · v3)** — 이후 사진 이동 · 추가 없음 · 자세한 기준은 [docs/split_policy.md](docs/split_policy.md) · 결과 [reports/split_report.md](reports/split_report.md)

| 역할 | 장수 | 촬영 묶음 (5분 간격) | 비고 |
|---|---|---|---|
| Train | 600 | T00(고정) · T01 · T03 · T05 · T06 · T07 · T10 · T12 · T13 · T15 · T17 앞 135장 | 깨끗한 사진 16 (배경 학습) |
| Validation | 75 | T02 · T04 통째 + T17 끝 15장 | 깨끗한 사진 10 · eval_exclude 4 |
| Frozen Test | 75 | T08 · T14 | eval_exclude 1 · Final 선택 뒤 1회만 |
| Bridge Holdout | 150 | T09 · T11 · T16 | dataset.yaml 에 넣지 않음 · 교과 14 용 |

- 나누는 단위: **capture_group (5분 촬영 묶음)** 통째 → 같은 김치 · 같은 이물이 두 역할에 걸치지 않게 (누수 방지) · 예외는 T17 끝 15장 1곳
- 누수 점검: `scripts/03b_check_phash.py` (pHash) → 묶음 경계 전부 거리 14 이상 · 거의 같은 사진 5장 `eval_exclude` → [reports/phash_check.csv](reports/phash_check.csv)
- 설정: [configs/dataset.yaml](configs/dataset.yaml) (상대경로 · 실제 Class 이름) · 목록: `manifests/train.csv · val.csv · test.csv · bridge_holdout.csv · split_manifest.csv`
- 분포: [reports/dataset_summary.csv](reports/dataset_summary.csv) · [reports/size_distribution.csv](reports/size_distribution.csv)

## 7. Baseline
TBD

## 8. Failure Analysis
TBD

## 9. Improvement
TBD

## 10. Final Model
TBD

## 11. Frozen Test
TBD

## 12. Detection / Auto Label
TBD

## 13. 알려진 한계
- **Split (10/15)**: 사진 900장 · 묶음 18개라 모든 조건을 동시에 맞추는 조합 없음 → 아래는 기록하고 평가 방법으로 대응
  - Validation 박스의 약 64% 가 Class 2 → 전체 mAP 와 **Class 별 P · R** 를 함께 보고
  - Validation 에 Class 3 · 5 가 적고 (10 · 14개) Class 6 은 0 → Class 6 은 Val 로 평가 불가
  - Bridge 의 Class 5 (236) 가 Train (170) 보다 많음 (T09 에 몰림)
  - Validation 이물만 사진 15장은 T17 과 같은 촬영 → 이물만 점수는 참고용
  - Test 에 깨끗한 김치 사진 0 → 이미지 단위 오판정은 Validation 깨끗한 사진 10장으로 확인
- 학습 · 평가 단계 한계: TBD

## 14. 교과 14 Handoff
TBD — docs/handoff_subject14.md

