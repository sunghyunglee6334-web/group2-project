# Split 기록 (MVP: 그룹 단위 층화 배정)

- Dataset Version: kimchi_v1 · 정책: group_stratified_mvp · gap 300s · seed 42(기록용)
- 산출물 1: manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
- split_manifest.csv SHA256: `40b6b1738f75c12f9a11abf0e4a1591e3e188c5e7069fe5d9b023ac99b8ba386`

## [2단계] 그룹 속성 / [3단계] 배정

| group_id   |   n_images | dates   | scene_mode         | diversity   | has_rare   |   n_objects |   empty_ratio |   d1 |   ambiguous | stratum                | split          |
|:-----------|-----------:|:--------|:-------------------|:------------|:-----------|------------:|--------------:|-----:|------------:|:-----------------------|:---------------|
| T00        |         50 | 04-10   | kimchi_with_target | 1-2         | True       |         252 |         0     |   40 |           0 | kimchi_with_target|1-2 | train          |
| T01        |          1 | 04-10   | normal_kimchi      | 0           | False      |           0 |         1     |    1 |           0 | normal_kimchi|0        | train          |
| T02        |         10 | 04-10   | normal_kimchi      | 0           | False      |           0 |         1     |    7 |           0 | normal_kimchi|0        | train          |
| T03        |         39 | 04-10   | kimchi_with_target | 5-6         | True       |          87 |         0.359 |   32 |           0 | kimchi_with_target|5-6 | train          |
| T04        |         50 | 04-10   | kimchi_with_target | 5-6         | False      |         269 |         0     |   35 |           1 | kimchi_with_target|5-6 | bridge_holdout |
| T05        |         48 | 04-11   | kimchi_with_target | 5-6         | False      |         247 |         0     |   37 |           3 | kimchi_with_target|5-6 | train          |
| T06        |         76 | 04-11   | kimchi_with_target | 5-6         | False      |         435 |         0     |   62 |           1 | kimchi_with_target|5-6 | train          |
| T07        |         26 | 04-11   | kimchi_with_target | 5-6         | False      |         169 |         0     |   22 |           0 | kimchi_with_target|5-6 | train          |
| T08        |         25 | 04-11   | kimchi_with_target | 1-2         | False      |         147 |         0     |   21 |           1 | kimchi_with_target|1-2 | test           |
| T09        |         75 | 04-11   | kimchi_with_target | 5-6         | False      |         398 |         0     |   61 |           0 | kimchi_with_target|5-6 | train          |
| T10        |         50 | 04-24   | kimchi_with_target | 5-6         | False      |         317 |         0     |   39 |           0 | kimchi_with_target|5-6 | val            |
| T11        |         25 | 04-24   | kimchi_with_target | 1-2         | False      |         141 |         0     |   21 |           0 | kimchi_with_target|1-2 | val            |
| T12        |         75 | 04-24   | kimchi_with_target | 5-6         | False      |         419 |         0     |   59 |          21 | kimchi_with_target|5-6 | train          |
| T13        |         50 | 04-24   | kimchi_with_target | 5-6         | False      |         288 |         0     |   43 |           0 | kimchi_with_target|5-6 | bridge_holdout |
| T14        |         50 | 04-24   | kimchi_with_target | 5-6         | True       |         281 |         0     |   20 |           0 | kimchi_with_target|5-6 | test           |
| T15        |         50 | 04-24   | kimchi_with_target | 5-6         | False      |         240 |         0     |    0 |           1 | kimchi_with_target|5-6 | train          |
| T16        |         50 | 04-24   | kimchi_with_target | 5-6         | False      |         266 |         0     |    0 |           0 | kimchi_with_target|5-6 | bridge_holdout |
| T17        |        150 | 05-13   | object_only        | 3-4         | False      |         449 |         0.007 |    0 |           0 | object_only|3-4        | train          |

## [4단계] split별 분포

| split          |   images |   groups |   d1_pct |   empty_pct |   ambiguous | dates                   |   scene:kimchi_with_target |   scene:object_only |   scene:normal_kimchi |   stratum:kimchi_with_target|5-6 |   stratum:normal_kimchi|0 |   stratum:kimchi_with_target|1-2 |   stratum:object_only|3-4 |   class:0 |   class:1 |   class:2 |   class:3 |   class:5 |   class:6 |
|:---------------|---------:|---------:|---------:|------------:|------------:|:------------------------|---------------------------:|--------------------:|----------------------:|---------------------------------:|--------------------------:|---------------------------------:|--------------------------:|----------:|----------:|----------:|----------:|----------:|----------:|
| train          |      600 |       11 |     53.5 |         4.3 |          26 | 04-10,04-11,04-24,05-13 |                        425 |                 151 |                    24 |                                7 |                         2 |                                1 |                         1 |       320 |      1170 |       293 |       343 |       320 |       250 |
| val            |       75 |        2 |     80   |         0   |           0 | 04-24                   |                         75 |                   0 |                     0 |                                1 |                         0 |                                1 |                         0 |         6 |       159 |       243 |        10 |        40 |         0 |
| test           |       75 |        2 |     54.7 |         0   |           1 | 04-11,04-24             |                         75 |                   0 |                     0 |                                1 |                         0 |                                1 |                         0 |        14 |       181 |       177 |        10 |        45 |         1 |
| bridge_holdout |      150 |        3 |     52   |         0   |           1 | 04-10,04-24             |                        150 |                   0 |                     0 |                                3 |                         0 |                                0 |                         0 |       369 |       155 |       224 |        15 |        60 |         0 |

## 검증

- ✅ 모든 이미지가 하나의 split에만 속함
- ✅ 같은 group_id가 여러 split에 걸치지 않음
- ✅ 같은 time_group이 여러 split에 걸치지 않음
- ✅ Train·Val과 Test에 같은 이미지 없음
- ✅ Bridge가 다른 split과 겹치지 않음
- ✅ manifests/train.csv 저장 (600장)
- ✅ manifests/val.csv 저장 (75장)
- ✅ manifests/test.csv 저장 (75장)
- ✅ manifests/bridge_holdout.csv 저장 (150장)
- ✅ split_manifest.csv = 네 파일의 합 (겹침 없음)

## 확인 필요

- [3-3] 모든 조건을 만족하는 배정이 없어 완화한 조건: Val·Test Class별 최소 객체 수 / 배경 이미지 Train 비율 50% → 30% / Train Class 객체 수가 가장 많아야 함  (완화 전 막힌 조건: train:배경 이미지 50% 미만 10회, train:Class 3 객체가 다른 split보다 적음 3회, train:Class 0 객체가 다른 split보다 적음 2회, train:Class 2 객체가 다른 split보다 적음 2회, train:Class 5 객체가 다른 split보다 적음 1회 | 후보 단계: bridge_holdout:장수(150±0) 1126회, bridge_holdout:출처 비율(55.6±10%p) 884회, bridge_holdout:애매한 라벨(≤1) 499회, test:출처 비율(55.6±10%p) 273회)
- Test·Bridge의 애매한 라벨 → eval_exclude=True: 250410_174414309990.jpg, 250411_140406550160.jpg

## 실행 로그

- [1-2] Δt > 300s 기준 time_group 18개
- [1-3] group_id 18개
- [1-4] 그룹 크기: 최소 1 · 중앙값 50 · 최대 150장
- [3-2] Train 보호: T17 — 층 'object_only|3-4'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-3] 조건 완화: Val·Test Class별 최소 객체 수
- [3-2] Train 보호: T17 — 층 'object_only|3-4'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-3] 조건 완화: 배경 이미지 Train 비율 50% → 30%
- [3-2] Train 보호: T17 — 층 'object_only|3-4'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-3] 조건 완화: Train Class 객체 수가 가장 많아야 함
- [3-2] Train 보호: T17 — 층 'object_only|3-4'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-3] 세 split 점수 합 4.45 (가장 작은 배정)
- [3-3] bridge_holdout: T04, T13, T16 (차이 합 1.62 · 층 0.58 · 장면 0.39 · Class 0.65 · 배경 0.29)
- [3-3] test: T08, T14 (차이 합 1.32 · 층 0.44 · 장면 0.39 · Class 0.42 · 배경 0.29)
- [3-3] val: T10, T11 (차이 합 1.51 · 층 0.44 · 장면 0.39 · Class 0.61 · 배경 0.29)
- [5단계] manifests/ 저장: split_manifest.csv, train/val/test/bridge_holdout.csv
