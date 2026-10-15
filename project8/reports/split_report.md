# Split 기록 (MVP: 그룹 단위 층화 배정)

- Dataset Version: kimchi_v1 · 정책: group_stratified_mvp · gap 300s · seed 42(기록용)
- 산출물 1: manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
- split_manifest.csv SHA256: `147bb32e1ceca5f771ce08994b2404771c799a29753aac622d665fe7a81ff8d9`

## [2단계] 그룹 속성 / [3단계] 배정

```
group_id  n_images dates         scene_mode diversity  has_rare  n_objects  empty_ratio  d1  ambiguous                stratum          split
     T00        50 04-10 kimchi_with_target       1-2      True        252        0.000  40          0 kimchi_with_target|1-2          train
     T01         1 04-10      normal_kimchi         0     False          0        1.000   1          0        normal_kimchi|0          train
     T02        10 04-10      normal_kimchi         0     False          0        1.000   7          0        normal_kimchi|0            val
     T03        39 04-10 kimchi_with_target       5-6      True         87        0.359  32          0 kimchi_with_target|5-6          train
     T04        50 04-10 kimchi_with_target       5-6     False        269        0.000  35          1 kimchi_with_target|5-6            val
     T05        48 04-11 kimchi_with_target       5-6     False        247        0.000  37          3 kimchi_with_target|5-6          train
     T06        76 04-11 kimchi_with_target       5-6     False        435        0.000  62          1 kimchi_with_target|5-6          train
     T07        26 04-11 kimchi_with_target       5-6     False        169        0.000  22          0 kimchi_with_target|5-6          train
     T08        25 04-11 kimchi_with_target       1-2     False        147        0.000  21          1 kimchi_with_target|1-2           test
     T09        75 04-11 kimchi_with_target       5-6     False        398        0.000  61          0 kimchi_with_target|5-6 bridge_holdout
     T10        50 04-24 kimchi_with_target       5-6     False        317        0.000  39          0 kimchi_with_target|5-6          train
     T11        25 04-24 kimchi_with_target       1-2     False        141        0.000  21          0 kimchi_with_target|1-2 bridge_holdout
     T12        75 04-24 kimchi_with_target       5-6     False        419        0.000  59         21 kimchi_with_target|5-6          train
     T13        50 04-24 kimchi_with_target       5-6     False        288        0.000  43          0 kimchi_with_target|5-6          train
     T14        50 04-24 kimchi_with_target       5-6      True        281        0.000  20          0 kimchi_with_target|5-6           test
     T15        50 04-24 kimchi_with_target       5-6     False        240        0.000   0          1 kimchi_with_target|5-6          train
     T16        50 04-24 kimchi_with_target       5-6     False        266        0.000   0          0 kimchi_with_target|5-6 bridge_holdout
     T17       135 05-13        object_only       3-4     False        400        0.007   0          0        object_only|3-4          train
   T17_V        15 05-13        object_only       3-4     False         49        0.000   0          0        object_only|3-4            val
```

## [4단계] split별 분포

```
         split  images  groups  d1_pct  empty_pct  ambiguous                   dates  scene:kimchi_with_target  scene:object_only  scene:normal_kimchi  stratum:kimchi_with_target|5-6  stratum:kimchi_with_target|1-2  stratum:normal_kimchi|0  stratum:object_only|3-4  class:0  class:1  class:2  class:3  class:5  class:6
         train     600      11    55.8        2.7         26 04-10,04-11,04-24,05-13                       450                135                   15                               8                               1                        1                        1      487     1104      507      336      170      250
           val      75       3    56.0       13.3          1             04-10,05-13                        50                 16                    9                               1                               0                        1                        1       29       60      205       10       14        0
          test      75       2    54.7        0.0          1             04-11,04-24                        75                  0                    0                               1                               1                        0                        0       14      181      177       10       45        1
bridge_holdout     150       3    54.7        0.0          0             04-11,04-24                       150                  0                    0                               2                               1                        0                        0      179      320       48       22      236        0
```

## [4-5] split × Class × bbox 크기

```
         split class  objects  small  small_pct  medium  medium_pct  large  large_pct
           all     0      709    236       33.3     236        33.3    237       33.4
bridge_holdout     0      179    146       81.6      33        18.4      0        0.0
          test     0       14      3       21.4       6        42.9      5       35.7
         train     0      487     77       15.8     194        39.8    216       44.4
           val     0       29     10       34.5       3        10.3     16       55.2
           all     1     1665    555       33.3     555        33.3    555       33.3
bridge_holdout     1      320     81       25.3     146        45.6     93       29.1
          test     1      181     89       49.2      59        32.6     33       18.2
         train     1     1104    372       33.7     323        29.3    409       37.0
           val     1       60     13       21.7      27        45.0     20       33.3
           all     2      937    312       33.3     312        33.3    313       33.4
bridge_holdout     2       48     19       39.6      13        27.1     16       33.3
          test     2      177     30       16.9     113        63.8     34       19.2
         train     2      507    194       38.3     130        25.6    183       36.1
           val     2      205     69       33.7      56        27.3     80       39.0
           all     3      378    126       33.3     126        33.3    126       33.3
bridge_holdout     3       22     10       45.5      10        45.5      2        9.1
          test     3       10      1       10.0       3        30.0      6       60.0
         train     3      336    113       33.6     110        32.7    113       33.6
           val     3       10      2       20.0       3        30.0      5       50.0
           all     5      465    155       33.3     155        33.3    155       33.3
bridge_holdout     5      236     22        9.3      67        28.4    147       62.3
          test     5       45     21       46.7      22        48.9      2        4.4
         train     5      170    103       60.6      63        37.1      4        2.4
           val     5       14      9       64.3       3        21.4      2       14.3
```

- 같은 위치·다른 이물 쌍: 0개 (reports/scene_pairs.csv)

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

```
time_group  장수  기존_validation  비율(%)      배정된 split
       T00  50             10     20          train
       T01   1              0      0          train
       T02  10              3     30            val
       T03  39              7     18          train
       T04  50             15     30            val
       T05  48             11     23          train
       T06  76             14     18          train
       T07  26              4     15          train
       T08  25              4     16           test
       T09  75             14     19 bridge_holdout
       T10  50             11     22          train
       T11  25              4     16 bridge_holdout
       T12  75             16     21          train
       T13  50              7     14          train
       T14  50             13     26           test
       T15  50              9     18          train
       T16  50              8     16 bridge_holdout
       T17 150             30     20          train
```

## 확인 필요

- [1-5] T17_V 15장은 T17와 같은 촬영 묶음(같은 이물 세트) → Val 점수가 실제보다 좋게 나올 수 있음 (same_bundle_split=True로 표시)
- [3-3] 모든 조건을 만족하는 배정이 없어 완화한 조건: Val·Test Class별 최소 객체 수 / 배경 이미지 Train 비율 50% → 30% / Train Class 객체 수가 가장 많아야 함  (완화 전 막힌 조건: train:Class 2 객체가 다른 split보다 적음 2회, train:Class 5 객체가 다른 split보다 적음 1회, train:Class 0 객체가 다른 split보다 적음 1회, train:Class 3 객체가 다른 split보다 적음 1회 | 후보 단계: bridge_holdout:출처 비율(55.6±10%p) 38회, bridge_holdout:애매한 라벨(≤1) 29회, test:출처 비율(55.6±10%p) 23회, test:날짜 수(≥2) 19회)
- Test·Bridge의 애매한 라벨 → eval_exclude=True: 250411_140406550160.jpg
- [4-5] bridge_holdout Class 0 크기 분포가 전체와 48%p 다름 (small 81.6% / medium 18.4% / large 0.0%)
- [4-5] test Class 2 크기 분포가 전체와 30%p 다름 (small 16.9% / medium 63.8% / large 19.2%)
- [4-5] val Class 5 크기 분포가 전체와 31%p 다름 (small 64.3% / medium 21.4% / large 14.3%)

## 실행 로그

- [2-4a] bbox 크기 경계(class_quantile, 학습 640px 기준 √넓이): small < {'0': 26.3, '1': 17.0, '2': 26.2, '3': 13.2, '5': 8.7, '6': 17.9}px ≤ medium < {'0': 39.4, '1': 27.9, '2': 34.0, '3': 15.8, '5': 21.7, '6': 19.8}px ≤ large
- [1-2] Δt > 300s 기준 time_group 18개
- [1-5] 기존 validation 연속 30장 발견 (T17) → 끝의 15장을 'T17_V' 그룹으로 떼어 Val 우선 배정
- [1-3] group_id 19개
- [1-4] 그룹 크기: 최소 1 · 중앙값 50 · 최대 135장
- [3-2] Train 보호: T17 — 이물만(object_only) 묶음 → Train에도 이물만 사진이 있어야 함
- [3-2] Train 보호: T01 — 층 'normal_kimchi|0'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-4] 기존 validation 블록 → Val 고정: T17_V, T02
- [3-3] 조건 완화: Val·Test Class별 최소 객체 수
- [3-2] Train 보호: T17 — 이물만(object_only) 묶음 → Train에도 이물만 사진이 있어야 함
- [3-2] Train 보호: T01 — 층 'normal_kimchi|0'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-4] 기존 validation 블록 → Val 고정: T17_V, T02
- [3-3] 조건 완화: 배경 이미지 Train 비율 50% → 30%
- [3-2] Train 보호: T17 — 이물만(object_only) 묶음 → Train에도 이물만 사진이 있어야 함
- [3-2] Train 보호: T01 — 층 'normal_kimchi|0'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-4] 기존 validation 블록 → Val 고정: T17_V, T02
- [3-3] 조건 완화: Train Class 객체 수가 가장 많아야 함
- [3-2] Train 보호: T17 — 이물만(object_only) 묶음 → Train에도 이물만 사진이 있어야 함
- [3-2] Train 보호: T01 — 층 'normal_kimchi|0'에 그룹이 하나뿐 (나누면 Train에서 이 층이 사라짐)
- [3-2] Train 보호: T00 — 희소 Class 6 이미지의 96% 보유
- [3-1] 층: kimchi_with_target|1-2 11%, kimchi_with_target|5-6 71%, normal_kimchi|0 1%, object_only|3-4 17%
- [3-1] 장면(이미지 기준): kimchi_with_target 80.6%, normal_kimchi 2.7%, object_only 16.8%
- [3-1] Class 객체 비율: 0 17%, 1 40%, 2 23%, 3 9%, 5 11%
- [3-4] 기존 validation 블록 → Val 고정: T17_V, T02
- [3-3] 점수 합 11.77 (가장 작은 배정)
- [3-3] bridge_holdout: T11, T16, T09 (차이 합 3.06 · 층 0.36 · 장면 0.39 · Class 0.47 · 배경 0.29)
- [3-3] test: T08, T14 (차이 합 3.01 · 층 0.44 · 장면 0.39 · Class 0.42 · 배경 0.29)
- [3-3] val: T17_V, T02, T04 (차이 합 5.71 · 층 0.31 · 장면 0.28 · Class 0.84 · 배경 1.04 · 기존 validation 44%)
- [5단계] manifests/ 저장: split_manifest.csv, train/val/test/bridge_holdout.csv
