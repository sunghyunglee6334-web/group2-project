# Split 기록 — kimchi_v4

- 정책: group_fixed_v4 · gap 300s · 배정 직접 지정 (묶음 쪼개기 없음)
- 산출물 1: manifests/split_manifest.csv, train.csv, val.csv, test.csv, bridge_holdout.csv
- split_manifest.csv SHA256: `e03bd5c2418b7c7eaa7ce895a74c3bc3db40731eef6103b08ba18ab15c8b94d2`

## 묶음과 배정

```
group_id  n_images dates         scene_mode class_union  n_objects  empty_ratio  d1  ambiguous          split
     T00        50 04-10 kimchi_with_target         5 6        252        0.000  40          0          train
     T01         1 04-10      normal_kimchi                      0        1.000   1          0            val
     T02        10 04-10      normal_kimchi                      0        1.000   7          0          train
     T03        39 04-10 kimchi_with_target 0 1 2 3 5 6         87        0.359  32          0            val
     T04        50 04-10 kimchi_with_target   0 1 2 3 5        269        0.000  35          1          train
     T05        48 04-11 kimchi_with_target   0 1 2 3 5        247        0.000  37          3          train
     T06        76 04-11 kimchi_with_target   0 1 2 3 5        435        0.000  62          1          train
     T07        26 04-11 kimchi_with_target   0 1 2 3 5        169        0.000  22          0            val
     T08        25 04-11 kimchi_with_target         1 5        147        0.000  21          1           test
     T09        75 04-11 kimchi_with_target   0 1 2 3 5        398        0.000  61          0 bridge_holdout
     T10        50 04-24 kimchi_with_target   0 1 2 3 5        317        0.000  39          0          train
     T11        25 04-24 kimchi_with_target         1 5        141        0.000  21          0 bridge_holdout
     T12        75 04-24 kimchi_with_target   0 1 2 3 5        419        0.000  59         21          train
     T13        50 04-24 kimchi_with_target   0 1 2 3 5        288        0.000  43          0          train
     T14        50 04-24 kimchi_with_target 0 1 2 3 5 6        281        0.000  20          0           test
     T15        50 04-24 kimchi_with_target   0 1 2 3 5        240        0.000   0          1          train
     T16        50 04-24 kimchi_with_target   0 1 2 3 5        266        0.000   0          0 bridge_holdout
     T17       150 05-13        object_only     0 1 2 3        449        0.007   0          0          train
```

## split별 분포

```
         split  images  groups  d1_pct  empty_pct  ambiguous                   dates  scene:kimchi_with_target  scene:object_only  scene:normal_kimchi  scene:none  class:0  class:1  class:2  class:3  class:5  class:6
         train     609      10    52.9        1.8         27 04-10,04-11,04-24,05-13                       449                149                    9           2      489     1019      673      323      163      249
           val      66       3    83.3       22.7          0             04-10,04-11                        51                  0                   15           0       27      145       39       23       21        1
          test      75       2    54.7        0.0          1             04-11,04-24                        75                  0                    0           0       14      181      177       10       45        1
bridge_holdout     150       3    54.7        0.0          0             04-11,04-24                       150                  0                    0           0      179      320       48       22      236        0
```

## 평가할 수 있는가 (Val·Test에 있는지)

```
                   항목  train  val  test  bridge_holdout 평가 가장 많은 묶음
              Class 0    489   27    14             179 가능  T12 27%
              Class 1   1019  145   181             320 가능  T06 22%
              Class 2    673   39   177              48 가능  T10 26%
              Class 3    323   23    10              22 가능  T15 46%
              Class 5    163   21    45             236 가능  T09 46%
              Class 6    249    1     1               0 불가  T00 99%
장면 kimchi_with_target    449   51    75             150 가능  T06 10%
              장면 none      2    0     0               0 불가  T02 50%
     장면 normal_kimchi      9   15     0               0 불가  T03 58%
       장면 object_only    149    0     0               0 불가 T17 100%
```

## Class × bbox 크기

```
         split class  objects  small  small_pct  medium  medium_pct  large  large_pct
           all     0      709    236       33.3     236        33.3    237       33.4
bridge_holdout     0      179    146       81.6      33        18.4      0        0.0
          test     0       14      3       21.4       6        42.9      5       35.7
         train     0      489     77       15.7     191        39.1    221       45.2
           val     0       27     10       37.0       6        22.2     11       40.7
           all     1     1665    555       33.3     555        33.3    555       33.3
bridge_holdout     1      320     81       25.3     146        45.6     93       29.1
          test     1      181     89       49.2      59        32.6     33       18.2
         train     1     1019    334       32.8     314        30.8    371       36.4
           val     1      145     51       35.2      36        24.8     58       40.0
           all     2      937    312       33.3     312        33.3    313       33.4
bridge_holdout     2       48     19       39.6      13        27.1     16       33.3
          test     2      177     30       16.9     113        63.8     34       19.2
         train     2      673    253       37.6     174        25.9    246       36.6
           val     2       39     10       25.6      12        30.8     17       43.6
           all     3      378    126       33.3     126        33.3    126       33.3
bridge_holdout     3       22     10       45.5      10        45.5      2        9.1
          test     3       10      1       10.0       3        30.0      6       60.0
         train     3      323    108       33.4     109        33.7    106       32.8
           val     3       23      7       30.4       4        17.4     12       52.2
           all     5      465    155       33.3     155        33.3    155       33.3
bridge_holdout     5      236     22        9.3      67        28.4    147       62.3
          test     5       45     21       46.7      22        48.9      2        4.4
         train     5      163    101       62.0      57        35.0      5        3.1
           val     5       21     11       52.4       9        42.9      1        4.8
           all     6      251     84       33.5      83        33.1     84       33.5
          test     6        1      1      100.0       0         0.0      0        0.0
         train     6      249     82       32.9      83        33.3     84       33.7
           val     6        1      1      100.0       0         0.0      0        0.0
```

## 검증

- ✅ 모든 이미지가 하나의 split에만 속함
- ✅ 같은 group_id가 여러 split에 걸치지 않음
- ✅ 같은 time_group이 여러 split에 걸치지 않음 (예외 없음)
- ✅ Train·Val과 Test에 같은 이미지 없음
- ✅ Bridge가 다른 split과 겹치지 않음
- ✅ manifests/train.csv 저장 (609장)
- ✅ manifests/val.csv 저장 (66장)
- ✅ manifests/test.csv 저장 (75장)
- ✅ manifests/bridge_holdout.csv 저장 (150장)
- ✅ split_manifest.csv = 네 파일의 합 (겹침 없음)
- ✅ train 폴더 복사 (609장)
- ✅ val 폴더 복사 (66장)
- ✅ test 폴더 복사 (75장)
- ✅ bridge_holdout 폴더 복사 (150장)

## 확인 필요

- Test·Bridge의 애매한 라벨 → eval_exclude=True: 250411_140406550160.jpg
- [4-4] Class 6: Val 1 · Test 1개 → 평가 불가 — T00 한 묶음에 99%가 몰려 있음
- [4-4] 장면 none: Val 0 · Test 0장 → 이 장면 점수는 내지 않음
- [4-4] 장면 normal_kimchi: Val 15 · Test 0장 → 이 장면 점수는 내지 않음
- [4-4] 장면 object_only: Val 0 · Test 0장 → 이 장면 점수는 내지 않음
- [4-5] bridge_holdout Class 0 크기 분포가 전체와 48%p 다름 (small 81.6% / medium 18.4% / large 0.0%)
- [4-5] test Class 2 크기 분포가 전체와 30%p 다름 (small 16.9% / medium 63.8% / large 19.2%)

## 실행 로그

- [1-2] Δt > 300s 기준 time_group 18개
- [1-3] group_id 18개
- [1-4] 묶음 크기: 최소 1 · 중앙값 50 · 최대 150장
- [3단계] val 66장: T01, T03, T07
- [3단계] test 75장: T08, T14
- [3단계] bridge_holdout 150장: T09, T11, T16
- [3단계] train 609장: 나머지 전부
- [5단계] manifests/ 저장
