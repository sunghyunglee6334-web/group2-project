# Smoke Test 기록 (smoke\_v1)

* 목적: 작은 데이터로 **데이터 → 학습 → 저장(best.pt) → 예측** 이 끝까지 도는지 확인하고, 960 · batch 16 의 GPU 메모리를 미리 잰다 (나중 960 실험 대비)
* **성능 판단용이 아님** (3 epoch · 30장 학습이라 mAP 가 낮은 게 정상)
* 실행: `scripts/05\_smoke\_train.py` 
* 날짜: 2026-10-16 

## 1\. 설정

|항목|값|
|-|-|
|Model|yolo11n.pt|
|Data|configs/smoke\_dataset.yaml|
|imgsz / batch / epochs|960 / 16 / 3 (`SMOKE\_CONFIG`, src/project\_config.py)|
|seed|42 (`BASELINE\_CONFIG\["seed"]`)|
|예측 conf|0.25 (`PRED\_CONF`)|
|환경|NVIDIA GeForce RTX 3060 12GB · ultralytics 8.4.175 · torch 2.14.1+cu130|

## 2\. Smoke Dataset

|split|이미지|라벨 TXT|빈 라벨(배경)|Box 수 (Class별)|
|-|-:|-:|-:|-|
|train|30|30|0|0:13 · 1:75 · 2:16 · 3:16 · 5:7 · 6:26 (총 153)|
|val|8|8|1|0:1 · 1:1 · 2:38 · 5:2 (총 42)|

* 뽑는 방식: data/yolo 의 train · val 에서 **seed 고정 무작위** 로 N\_TRAIN = 30, N\_VAL = 8 장 (다시 돌려도 같은 사진)
* 이유: 처음에 이름순 앞쪽을 뽑았더니 val 8장이 모두 정상 김치 묶음(T02, Box 0개)에 몰려 mAP 가 0 으로 나옴 → 여러 촬영 묶음이 섞이게 바꿈
* 한계: val 은 Class 2(branch) 에 몰려 있고 Class 3 · 4 · 6 은 val 에 없음 → Class별 지표는 의미 없음

## 3\. 결과

|epoch|train box / cls / dfl loss|val box / cls / dfl loss|Precision|Recall|mAP50|mAP50-95|
|-:|-|-|-:|-:|-:|-:|
|1|1.437 / 11.789 / 1.229|1.302 / 6.407 / 1.386|0.00044|0.25|0.00401|0.00361|
|2|1.381 / 11.700 / 1.172|1.271 / 6.391 / 1.355|0.00042|0.25|0.00307|0.00246|
|3|1.352 / 10.238 / 1.227|1.282 / 6.421 / 1.357|0.00038|0.25|0.00251|0.00201|

* train loss 는 내려감 (cls 11.79 → 10.24) → 학습 루프 정상
* mAP 는 거의 0 → 3 epoch 에서는 예상된 값. 참고: baseline\_v1 (640 · 100 epoch, 전체 데이터) 은 val mAP50 0.658
* 재현성: 같은 설정으로 다시 돌렸을 때 loss · 지표가 소수점까지 같고 시간(time) 열만 달라짐 (git diff 로 확인)

## 4\. GPU 메모리 (reports/smoke\_gpu\_memory.json)

|imgsz|batch|peak reserved|peak allocated|전체|
|-:|-:|-:|-:|-:|
|960|16|4.86 GB|4.47 GB|12.0 GB|

* yolo11n 기준 960 · batch 16 은 여유 있음 (약 40%). 더 큰 모델(s/m)로 960 을 돌릴 때는 따로 다시 재야 함

## 5\. 예측 확인 (runs/predict/smoke\_v1/250410\_155734186034.jpg)

* 예측 대상: smoke val 의 **이름순 첫 장** (`list\_images(...)\[0]`) → 우연히 **빈 라벨(배경) 사진** 이 걸림

  * data/smoke/labels/val 과 data/yolo/labels/val 의 같은 이름 TXT 모두 비어 있음 (GT Box 0개)
* 그려진 Box 2개, 둘 다 `disease\_browning`

  * conf 0.89: 오른쪽 위 하얀 배추 줄기 한 조각 → 오탐(FP)
  * conf 0.34: 왼쪽 절반을 거의 덮는 큰 Box → 오탐(FP)
* 사진에 빨간/분홍 조각(고무장갑으로 보임)이 6\~7개 있지만 라벨 없음

  * split\_manifest 확인: 정상 김치 묶음 **T02**, 원본 Box 5개 → 최종 0개, issue "class4 고무장갑" (REVIEWED)
  * 즉 라벨 누락이 아니라 **사용하지 않는 Class 4(`rubber\_glove\_unused`) 를 의도적으로 지운 것** → 모델 입장에선 고무장갑이 "배경" 으로 학습됨

## 6\. 판정

|확인 항목|결과|
|-|-|
|Dataset YAML · 이미지/라벨 짝|통과|
|학습 3 epoch 완료 · loss 감소|통과|
|weights/best.pt 저장 (5.5MB, 2026-10-16 12:05)|통과|
|960 · batch 16 GPU 메모리|통과 (4.86 / 12 GB)|
|best.pt 로 예측 · 이미지 저장|통과 (단, 배경 사진이라 Box 위치 검증은 못 함)|

**결론: End-to-End 파이프라인 정상 동작. 본 실험 진행 가능.**

## 

## 산출물

* runs/smoke\_v1/ (args.yaml, results.csv, results.png, confusion\_matrix, PR/F1 curve, weights/best.pt)
* runs/predict/smoke\_v1/250410\_155734186034.jpg
* reports/smoke\_gpu\_memory.json
* configs/smoke\_dataset.yaml · data/smoke/

