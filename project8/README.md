# project8 — 교과 8 조각김치 이물검출 객체검출 (YOLO11n)

> 데이터(JPG · TXT) · Weight(.pt) · runs 결과 이미지는 NDA 로 Git 에 올리지 않습니다.

## 1. 프로젝트 목적
교과 7 FINAL 900장으로 YOLO11n 을 학습 · 평가 · 실패분석 · 한 변수 개선 → Final Model · Frozen Test · Detection · Auto Label 까지 완성

## 2. 교과 7 → 교과 8 연결
- 교과 7 라벨링 프로그램 · 산출물: [../project7](../project7)
- 교과 7 FINAL 위치: TBD (10/15 FINAL 확정 후)

## 3. Dataset
- JPG 900 / YOLO TXT 900 · Dataset 1 (train) · Dataset 2 (train · validation)
- scene_type: kimchi_with_target · normal_kimchi · object_only · other_review
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
- Python: TBD · PyTorch: TBD · Ultralytics: TBD · GPU: TBD
- 설치: `cd project8 && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## 6. Dataset Split (Train · Validation · Frozen Test · Bridge Holdout)
TBD — docs/split_policy.md

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
TBD

## 14. 교과 14 Handoff
TBD — docs/handoff_subject14.md
