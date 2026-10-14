# Split 기록 (MVP: 그룹 단위 층화 배정)

- Dataset Version: kimchi_v1 · 정책: group_stratified_mvp · gap 300s · seed 42(기록용)
- 산출물 1: manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
- split_manifest.csv SHA256: `712bea8d4bab46387d1d6408ea13c2056a7d55bac471a30c032b3243d4de5208`

## [2단계] 그룹 속성 / [3단계] 배정

| group_id   |   n_images | dates   | scene_mode         | diversity   | has_rare   |   n_objects |   empty_ratio |   d1 |   ambiguous | stratum                | split          |
|:-----------|-----------:|:--------|:-------------------|:------------|:-----------|------------:|--------------:|-----:|------------:|:-----------------------|:---------------|
| T00        |         50 | 04-10   | kimchi_with_target | 1-2         | True       |         252 |         0     |   40 |           0 | kimchi_with_target|1-2 | train          |
| T01        |          1 | 04-10   | normal_kimchi      | 0           | False      |           0 |         1     |    1 |           0 | normal_kimchi|0        | train          |
| T02        |         10 | 04-10   | normal_kimchi      | 0           | False      |           0 |         1     |    7 |           0 | normal_kimchi|0        | train          |
| T03_R      |         32 | 04-10   | kimchi_with_target | 5-6         | True       |          71 |         0.375 |   32 |           0 | kimchi_with_target|5-6 | train          |
| T03_V      |          7 | 04-10   | kimchi_with_target | 3-4         | False      |          16 |         0.286 |    0 |           0 | kimchi_with_target|3-4 | val            |
| T04_R      |         35 | 04-10   | kimchi_with_target | 5-6         | False      |         192 |         0     |   35 |           1 | kimchi_with_target|5-6 | train          |
| T04_V      |         15 | 04-10   | kimchi_with_target | 5-6         | False      |          77 |         0     |    0 |           0 | kimchi_with_target|5-6 | val            |
| T05        |         48 | 04-11   | kimchi_with_target | 5-6         | False      |         247 |         0     |   37 |           3 | kimchi_with_target|5-6 | train          |
| T06        |         76 | 04-11   | kimchi_with_target | 5-6         | False      |         435 |         0     |   62 |           1 | kimchi_with_target|5-6 | train          |
| T07        |         26 | 04-11   | kimchi_with_target | 5-6         | False      |         169 |         0     |   22 |           0 | kimchi_with_target|5-6 | train          |
| T08        |         25 | 04-11   | kimchi_with_target | 1-2         | False      |         147 |         0     |   21 |           1 | kimchi_with_target|1-2 | test           |
| T09        |         75 | 04-11   | kimchi_with_target | 5-6         | False      |         398 |         0     |   61 |           0 | kimchi_with_target|5-6 | bridge_holdout |
| T10        |         50 | 04-24   | kimchi_with_target | 5-6         | False      |         317 |         0     |   39 |           0 | kimchi_with_target|5-6 | train          |
| T11        |         25 | 04-24   | kimchi_with_target | 1-2         | False      |         141 |         0     |   21 |           0 | kimchi_with_target|1-2 | bridge_holdout |
| T12_R      |         59 | 04-24   | kimchi_with_target | 5-6         | False      |         329 |         0     |   59 |          21 | kimchi_with_target|5-6 | train          |
| T12_V      |         16 | 04-24   | kimchi_with_target | 5-6         | False      |          90 |         0     |    0 |           0 | kimchi_with_target|5-6 | val            |
| T13_R      |         43 | 04-24   | kimchi_with_target | 5-6         | False      |         246 |         0     |   43 |           0 | kimchi_with_target|5-6 | train          |
| T13_V      |          7 | 04-24   | kimchi_with_target | 5-6         | False      |          42 |         0     |    0 |           0 | kimchi_with_target|5-6 | val            |
| T14        |         50 | 04-24   | kimchi_with_target | 5-6         | True       |         281 |         0     |   20 |           0 | kimchi_with_target|5-6 | test           |
| T15        |         50 | 04-24   | kimchi_with_target | 5-6         | False      |         240 |         0     |    0 |           1 | kimchi_with_target|5-6 | train          |
| T16        |         50 | 04-24   | kimchi_with_target | 5-6         | False      |         266 |         0     |    0 |           0 | kimchi_with_target|5-6 | bridge_holdout |
| T17_R      |        120 | 05-13   | object_only        | 3-4         | False      |         355 |         0.008 |    0 |           0 | object_only|3-4        | train          |
| T17_V      |         30 | 05-13   | object_only        | 3-4         | False      |          94 |         0     |    0 |           0 | object_only|3-4        | val            |

## [4단계] split별 분포

| split          |   images |   groups |   d1_pct |   empty_pct |   ambiguous | dates                   |   scene:kimchi_with_target |   scene:object_only |   scene:normal_kimchi |   stratum:kimchi_with_target|5-6 |   stratum:normal_kimchi|0 |   stratum:kimchi_with_target|1-2 |   stratum:object_only|3-4 |   class:0 |   class:1 |   class:2 |   class:3 |   class:5 |   class:6 |   stratum:kimchi_with_target|3-4 |
|:---------------|---------:|---------:|---------:|------------:|------------:|:------------------------|---------------------------:|--------------------:|----------------------:|---------------------------------:|--------------------------:|---------------------------------:|--------------------------:|----------:|----------:|----------:|----------:|----------:|----------:|---------------------------------:|
| train          |      600 |       13 |     62.8 |         4   |          27 | 04-10,04-11,04-24,05-13 |                        457 |                 121 |                    22 |                                9 |                         2 |                                1 |                         1 |       429 |      1070 |       620 |       318 |       166 |       250 |                                0 |
| val            |       75 |        5 |      0   |         2.7 |           0 | 04-10,04-24,05-13       |                         43 |                  30 |                     2 |                                3 |                         0 |                                0 |                         1 |        87 |        94 |        92 |        28 |        18 |         0 |                                1 |
| test           |       75 |        2 |     54.7 |         0   |           1 | 04-11,04-24             |                         75 |                   0 |                     0 |                                1 |                         0 |                                1 |                         0 |        14 |       181 |       177 |        10 |        45 |         1 |                                0 |
| bridge_holdout |      150 |        3 |     54.7 |         0   |           0 | 04-11,04-24             |                        150 |                   0 |                     0 |                                2 |                         0 |                                1 |                         0 |       179 |       320 |        48 |        22 |       236 |         0 |                                0 |

## 검증

- ✅ 모든 이미지가 하나의 split에만 속함
- ✅ 같은 group_id가 여러 split에 걸치지 않음
- ✅ 같은 time_group이 여러 split에 걸치지 않음 (Val 조각으로 나눈 묶음은 예외)
- ✅ Train·Val과 Test에 같은 이미지 없음
- ✅ Bridge가 다른 split과 겹치지 않음
- ✅ manifests/train.csv 저장 (600장)
- ✅ manifests/val.csv 저장 (75장)
- ✅ manifests/test.csv 저장 (75장)
- ✅ manifests/bridge_holdout.csv 저장 (150장)
- ✅ split_manifest.csv = 네 파일의 합 (겹침 없음)

## 기존 validation 검토

- 기존 validation 180장이 촬영 묶음 17개에 14~30%씩 흩어져 있음 (사진 단위 무작위 추출로 보임)
- 그중 135장은 60초 안에 기존 train 사진이 바로 옆에 있음 (같은 묶음 = 같은 이물 세트)
- 사진 단위로 Val에 넣으면 같은 묶음이 Train·Val로 갈라져 누수 → 사용하지 않음
- 대신 묶음 단위로 반영: Val을 고를 때 기존 validation 비율이 높은 묶음에 가산점 ([3-4] orig_val_preference)
  (모든 묶음 비율이 14~30%로 비슷해 효과는 크지 않을 수 있음)

| time_group   |   장수 |   기존_validation |   비율(%) | 배정된 split      |
|:-------------|-----:|----------------:|--------:|:---------------|
| T00          |   50 |              10 |      20 | train          |
| T01          |    1 |               0 |       0 | train          |
| T02          |   10 |               3 |      30 | train          |
| T03          |   39 |               7 |      18 | train          |
| T04          |   50 |              15 |      30 | train          |
| T05          |   48 |              11 |      23 | train          |
| T06          |   76 |              14 |      18 | train          |
| T07          |   26 |               4 |      15 | train          |
| T08          |   25 |               4 |      16 | test           |
| T09          |   75 |              14 |      19 | bridge_holdout |
| T10          |   50 |              11 |      22 | train          |
| T11          |   25 |               4 |      16 | bridge_holdout |
| T12          |   75 |              16 |      21 | train          |
| T13          |   50 |               7 |      14 | train          |
| T14          |   50 |              13 |      26 | test           |
| T15          |   50 |               9 |      18 | train          |
| T16          |   50 |               8 |      16 | bridge_holdout |
| T17          |  150 |              30 |      20 | train          |

## 확인 필요

- [3-3] 모든 조건을 만족하는 배정이 없어 완화한 조건: Val·Test Class별 최소 객체 수 / 배경 이미지 Train 비율 50% → 30% / Train Class 객체 수가 가장 많아야 함  (완화 전: [3-0] Val 후보 60개 모두 Bridge·Test 배정 실패. 막힌 조건: train:Class 0 객체가 다른 split보다 적음 1회 (6회); train:Class 2 객체가 다른 split보다 적음 1회 (5회); train:Class 2 객체가 다른 split보다 적음 2회, train:Class 0 객체가 다른 split보다 적음 1회 ()
- [3-0] Val은 기존 validation 사진으로 구성 → 같은 묶음(T03, T04, T12, T13, T17)의 나머지가 Train에 있어 Val 점수가 실제보다 좋게 나올 수 있음 (same_bundle_split=True)
- Test·Bridge의 애매한 라벨 → eval_exclude=True: 250411_140406550160.jpg

## 실행 로그

- [1-2] Δt > 300s 기준 time_group 18개
- [1-3] group_id 18개
- [1-4] 그룹 크기: 최소 1 · 중앙값 50 · 최대 150장
- [3-3] 조건 완화: Val·Test Class별 최소 객체 수
- [3-3] 조건 완화: 배경 이미지 Train 비율 50% → 30%
- [3-3] 조건 완화: Train Class 객체 수가 가장 많아야 함
- [3-0] Val 먼저: 기존 validation 180장 → 묶음별 V 조각 17개 중 T03_V, T04_V, T12_V, T13_V, T17_V 선택 (75장)
- [3-0] 조각을 내준 묶음의 나머지 → Train: T03_R, T04_R, T12_R, T13_R, T17_R
- [3-2] Train 보호: T17_R — 이물만(object_only) 묶음 → Train에도 이물만 사진이 있어야 함
- [3-2] Train 보호: T17_V — 이물만(object_only) 묶음 → Train에도 이물만 사진이 있어야 함
- [3-2] Train 보호: T03_V — 층 'kimchi_with_target|3-4'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-3] 점수 합 2.65 (가장 작은 배정)
- [3-3] val: T03_V, T04_V, T12_V, T13_V, T17_V (차이 합 1.10 · 층 0.56 · 장면 0.46 · Class 0.33 · 배경 0.02)
- [3-3] bridge_holdout: T09, T11, T16 (차이 합 1.32 · 층 0.36 · 장면 0.39 · Class 0.47 · 배경 0.29)
- [3-3] test: T08, T14 (차이 합 1.32 · 층 0.44 · 장면 0.39 · Class 0.42 · 배경 0.29)
- [3-3] val: T03_V, T04_V, T12_V, T13_V, T17_V (점수 1.35)
- [5단계] manifests/ 저장: split_manifest.csv, train/val/test/bridge_holdout.csv
