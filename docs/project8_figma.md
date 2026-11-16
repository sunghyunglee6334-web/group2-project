# 교과 8 Figma 보드 — 객체검출

팀 Figma 파일 **2조 · 교과8.** 페이지를 문서로 옮겼습니다. 전체 흐름 → Data · Split → Smoke Test → Baseline → Experiment → Final 순서입니다.

- 교과 8 보드에는 김치 원본 사진이 없어 블러 처리한 그림은 없습니다 (표 · 그래프 · 도식만).
- 그림을 클릭하면 크게 볼 수 있습니다. · 교과 7 보드 → [project7_figma.md](project7_figma.md)

<br>

## 1. 전체 흐름 · 요구사항 · 역할

![교과 8 전체 진행 흐름도](figma/project8/01_flow.png)

![교과 8 요구사항](figma/project8/02_requirements.png)

![교과 8 역할별 작업 산출물 전달 흐름](figma/project8/03_role_board.png)

<br>

## 2. Data / QA — Dataset Audit · Split

### Dataset Audit

![교과 7 FINAL Dataset Audit](figma/project8/10_dataset_audit.png)

### Split 기준 — 왜 묶음 단위로 나누나

![사진 900장을 4개 상자로 나누는 방법](figma/project8/11_split_4boxes.png)

![capture_group 정하는 방법](figma/project8/12_capture_group.png)

![Split 추천안 같은 이물 세트 단위](figma/project8/13_split_proposal.png)

### 최종 Split v4-B (609 / 66 / 75 / 150)

![Split 절차 흐름도 v4](figma/project8/14_split_flow_v4.png)

![Split 결과 kimchi_v4 최종](figma/project8/15_split_result_v4.png)

![Split 결과 kimchi_v4 상세](figma/project8/16_split_detail_v4.png)

![이전 코드 vs v4 vs v4-B 비교와 이슈노트](figma/project8/17_split_code_compare.png)

![파·고추 Class 6 T00 나누기 점검](figma/project8/18_class6_check.png)

![촬영 그룹별 육안 검수 Human QA 결과](figma/project8/19_human_qa.png)

<details>
<summary><b>Split 버전 기록 (v1 → v2 → v3 → v4)</b> — 누수를 막기까지 바뀐 과정</summary>

![Split 결과 kimchi_v1](figma/project8/20_split_v1.png)

![Split 결과 kimchi_v2](figma/project8/21_split_v2.png)

![Split 차이 kimchi_v2 → v3](figma/project8/22_split_v2_v3.png)

![Split 결과 kimchi_v3](figma/project8/23_split_v3.png)

![Split 절차 흐름도 v3](figma/project8/24_split_flow_v3.png)

![Split 결과 5분 간격 v3](figma/project8/25_split_result_v3.png)

![이전 코드 vs MVP vs v3 비교와 이슈노트](figma/project8/26_split_code_v3.png)

![Split 결과 kimchi_v4 와 pHash 확인](figma/project8/27_split_v4_phash.png)

</details>

<br>

## 3. Smoke Test

![Smoke Test 파이프라인 끝까지 동작](figma/project8/30_smoke.png)

<br>

## 4. Baseline — 평가 · 실패 분석

Split v4-B 기준 재평가(10/20) 결과입니다.

![Baseline 결과 종합](figma/project8/40_baseline_summary.png)

![Baseline 평가와 실패분석](figma/project8/41_baseline_failure.png)

![Baseline 상세 결과](figma/project8/42_baseline_detail.png)

![Baseline 결과 그림 해석 가이드](figma/project8/43_baseline_guide.png)

![Baseline IoU 분석](figma/project8/44_baseline_iou.png)

<details>
<summary><b>이전 Baseline 보드 (10/19 · Split v4-B 확정 전)</b></summary>

![Baseline 상세 결과 10/19](figma/project8/45_baseline_detail_v1.png)

![Baseline 평가와 실패분석 10/19](figma/project8/46_baseline_failure_v1.png)

</details>

<br>

## 5. Experiment — 실패 분석 → 개선 실험 → Final Model

![Experiment 실패 분석 개선 실험 Final Model](figma/project8/50_experiment.png)

<br>

## 6. Final — Frozen Test

![Baseline vs Final EXP003 Frozen Test 결과 비교](figma/project8/60_final_frozen_test.png)

<br>

## 관련 문서

| 내용 | 문서 |
|---|---|
| 실행 방법 · 결과 요약 | [project8 README](../project8/README.md) |
| Split 기준 | [split_policy](../project8/docs/split_policy.md) |
| Final 선택 근거 | [final_model_selection](../project8/reports/final_model_selection.md) |
