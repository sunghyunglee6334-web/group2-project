# Split 요약

- 원본: `data/final`
- 라벨 30%+ 겹침 쌍 107개 → 묶음 51개, 155장 (전부 train)

## split × scene_type

| split | 김치+객체 | 객체 단독 | 정상 김치(+none) | 합계 |
|---|---|---|---|---|
| train | 455 | 119 | 26 | 600 |
| val | 45 | 30 | 0 | 75 |
| test | 75 | 0 | 0 | 75 |
| bridge_holdout | 150 | 0 | 0 | 150 |

## split별 class 포함 이미지 비율(%)

| class | train | val | test | bridge_holdout |
|---|---|---|---|---|
| 0 leaf_paper | 29.5 | 33.3 | 34.7 | 38.0 |
| 1 plastic_stone_metal | 59.3 | 69.3 | 61.3 | 62.7 |
| 2 branch | 38.5 | 46.7 | 49.3 | 46.0 |
| 3 insect | 22.5 | 21.3 | 20.0 | 20.0 |
| 5 disease_browning | 23.3 | 20.0 | 37.3 | 38.0 |
| 6 green_onion_pepper | 7.2 | 2.7 | 4.0 | 2.7 |

## 생성된 폴더

- `data/yolo/images|labels/train|val|test`
- `data/bridge_holdout/images|labels`
- `configs/dataset.yaml`
