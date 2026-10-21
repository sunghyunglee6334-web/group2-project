---
tags:
  - 교과7
  - 조각김치
  - 작업기록
project: 조각김치 이물검출 라벨링 (교과 7)
name: 2조
updated: 2026-10-16
---

# 10-13

> [!info] 10-13 한 줄 요약
> **1.** 팀 회의 및 프로젝트 파트 분배
> **2.** 교과 7 final 데이터 넘겨 받기
> **3.** Data 파트 작업시작
> 4. Evaluation 파트 코딩 3개 작업 완료

- 교과 7로 Final data 받은 후 dataset audit.py 코딩 시작

- Evaluation 파트 코딩
	  - src/detector.py
	  - src/label_visualizer.py 
	  - scripts/07_evaluate_baseline.py
	  - 이후 Data 파트 업무 분담하여 split_builder.py 담당하기로 결정


# 10-14

> [!info] 10-14 한 줄 요약
> **1.** Data 파트 진행상황 확인
> **2.** Data 파트 코딩 진행
> **3.** Train 파트 Baseline 모델 코딩 진행

- Data
	Dataset_audit.py 진행 완료 및 split_bulider.py 코딩 진행
	split_policy 검토 후 split 기준 정책 논의 및 1차 작성
	1차 분류 결과 확인 -> 특정 항목에 해당되는 사진이 한 그룹으로만 분류되는 등 학습용으로 적절치 않은 분류임을 확인

- Train
	Baseline 모델 코딩 진행

- Evalution
	label_visualizer.py 수정


# 10-15

> [!info] 10-15 한 줄 요약
> **1.** Data split 완료
> **2.** 관련 산출물 확인 및 기준서 작성 완료
> **3.** Baseline 모델 코딩 1차 완료
> **4.** Evalution 파트 코딩 진행

- README 검토 및 수정

- Data
	- 분할된 데이터들 확인하여 split 확정 / 관련 파일 git 업로드
		configs/dataset.yaml
		manifests/split_manifest.csv
		reports/split_report.md, dataset_summary.csv
		docs/split_policy.md
		scripts/03b_check_phash.py
		src/split_builder.py
		tests/test_split_builder.py

- Train
	Baseline 모델 코드를 Data 파트 관련 파일에 맞춰 수정
	split 완료 후 데이터 받으면 바로 smoke test 가능하게끔 준비
	scripts/05_smoke_train.py, 06_train_baseline 완료
  
- Evalution
	scripts/08_compare_gt_pred.py 완료
	src/failure_analyzer.py 완료
	test_failure_analyzer.py 진행


# 10-16

> [!info] 10-16 한 줄 요약
> **1.** Baseline 모델 smoke test
> **2.** 첫 학습과 결과 validation 분석
> **3.** improve 모델 작업 시작

Evalution
	
	scripts/10_fn_by_size.py 완료
	reports/fn_by_size.csv, iou_by_box.csv, failure_analysis.csv 완료
	src/failure_analyzer.py, label_visualizer.py 완료
	docs/failure_Analysis.md 작성
	demo/failure_analysis NDA상 jpg 커밋 불가 팀내 공유

Data
	split 된 데이터에 누수 위험 확인
	split 관련 코드 수정 및 재진행
	split_builder.py
	  1. 그룹 분할 경로와 실행 설정의 덮어쓰기 제거
	  2. 기본 묶음·최종 그룹 식별자 보존. 
	  3. 기존 validation 우선은 그룹 단위 선호 조건으로만 적용.
	  4. 조건을 만족하는 배정이 없으면 그룹 분할로 해결하지 않음.
	  5. same_bundle_split 검증 제외 제거.
	  6. 확인된 동일·파생 관계의 split 간 분할 검사, 실패 시 최종 저장·복사 차단.


# 10-19

> [!info] 10-19 한 줄 요약
> **1.** Data 다시 split 후 재배포
> **2.** Baseline 모델 학습 후 결과 분석
> **3.** improve 모델 작업

Data
	split 재실시에 따른 관련 문서 갱신
	재분류 후 데이터 확정 및 배포

Train
	재배포 된 데이터로 다시 smoke test 및 basline 학습
	관련 산출물 확인

Experiment
	결과 분석에서 개선 근거 탐색
	이미지 사이즈를 키워 개선 시도


# 10-20

> [!info] 10-20 한 줄 요약
> **1.** Final 모델 확정
> **2.** Final 모델의 성능 평가 진행
> **3.** 해당 모델의 이미지 디텍션과 Auto Label 코드 작성 및 테스트
> **4.** 위 코드를 교과 7 라벨링 프로그램 Human review 연결

Experiment
	개선 총 4차까지 진행
	4차 모델은 정밀도 하락 확인되어 3차로 final 모델 확정
	관련 산출물 확인

Evalution
	해당 모델의 성능평가 진행
	관련 산출물 확인

Inference
	확정된 Final 모델로 이미지 detection과 auto_label, 교과7의 라벨링 프로그램으로 human review 기능 구현과 테스트 실행
	
	Project8
      src/inference.py, auto_label.py, auto_label_review.py
      scripts/14_predict_images.py, 15_auto_label.py
    
	Project7
	  src/bbox/session.py
	  src/ui/app.py‎‎
	  src/ui/panels.py



# 10-21

> [!info] 10-21 한 줄 요약
> **1.** Acceptance Test.md 작성
> **2.** 교과 14 인계 Handoff 작성
> **3.** 전체 발표 준비

서기
	팀장이 각 파트별 진행 항목 확인하여 해당 내용 Acceptance Test.md 작성
	교과 14 Handoff.md 작성

팀 전체 발표 준비
	ppt 작성
	본인 파트와 전체 프로젝트 진행 흐름 확인
	예상 질문 준비