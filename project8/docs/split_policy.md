# Split 정책 (split_policy.md)

- 상태: **초안 v0.2** — 수량 확정, 그룹 규칙은 육안 확인 후 확정
- 작성일: 2026-10-14 / 작성: 교과 8 Data 담당
- 대상: 교과 7 FINAL Dataset 900장 (`manifest_final.csv`)
- 도구: `group_candidates.py` → `split_builder.py`
- 미확정 표시: `TODO(기준선)`

> **원칙: 비율보다 누수를 막고 역할을 고정하는 것이 더 중요하다.**

## 0. 수량 (팀 결정, 2026-10-14)

| 역할 | 장수 | 비율 | 그룹 수 |
|---|---|---|---|
| Train | 600 | 66.7% | 22 (25장 그룹 17개 + 25장이 아닌 그룹 5개 전부) |
| Validation | 75 | 8.3% | 3 (25장 그룹) |
| Frozen Test | 75 | 8.3% | 3 (25장 그룹) |
| Bridge Holdout | 150 | 16.7% | 6 (25장 그룹) |
| 합계 | 900 | 100% | 34 |

- 25장이 아닌 그룹 5개(36·39·48·26·26장 = 175장)는 모두 Train → Val·Test·Bridge 수량이 정확히 맞음

---

## 1. 역할별 정책

### Bridge Holdout
- 교과 8 Train / Validation / Frozen Test와 **가장 먼저, 별도로** 분리
- 교과 8 학습·튜닝·모델 선택에 사용하지 않음 (열어보지 않음)
- 교과 14 연결용으로 보존
- 수량: 150장 (`capture_group` 6개)
- TODO(기준선): 교과 14에서 확인할 목적에 맞춰 그룹 선택
  - 후보 A: 가장 최근 kimchi_with_target 그룹 (시간상 새로운 데이터)
  - 후보 B: 날짜별 무작위 그룹 (Test와 같은 분포)

### Frozen Test
- Bridge를 뺀 **개발용 후보 Pool**에서 `capture_group` 단위로 별도 분리
- Final Model을 선택한 뒤 **마지막 평가에만** 사용
- 한 번 정하면 변경하지 않음 (변경 시 정책 버전을 올리고 사유 기록)
- 수량: 75장 (그룹 3개)

### Validation
- 가이드 기준: 기존 Dataset 2 / validation을 우선 후보로 검토
- **검토 결과 (2-4 참고): 사용하지 않음**
  - 누수 위험: 기존 validation 180장 중 135장이 60초 안의 train 사진과 인접
  - 수량 불일치: 기존 180장 ≠ 결정된 75장
  - → `capture_group` 단위로 Pool에서 새로 분리 (75장, 그룹 3개)
  - 기존 `original_split` 열은 참고용으로 보존
- Baseline과 Improved 비교에 사용
- 수량: 75장 (그룹 3개)

### Train
- 나머지 개발용 Pool

### 공통
- `source_dataset` / `original_split` / `scene_type` 열은 지우지 않고 보존
- 동일 `capture_group`은 한 역할에만 배정
- Class / scene_type 분포를 **함께** 확인 (4장)

---

## 2. capture_group

### 2-1. 파일명 시간 정보 (사실)
- 900장 모두 `YYMMDD_HHMMSS + 마이크로초` 형식, 중복 시각 없음
  - 예: `250410_144403911987.jpg` → 2025-04-10 14:44:03.91
- 촬영일 4일: 04-10(150) / 04-11(250) / 04-24(350) / 05-13(150)
- 연속 사진 간격은 대부분 20~60초. 10초 미만은 49건, 1초 미만은 1건
- 5분 초과 간격으로 끊으면 18묶음, 크기는 대부분 25의 배수

### 2-2. 아직 단정하지 않는 것
- 이 시각이 **카메라 캡처 시각**인지 (저장·내보내기 시각이 아닌지) — TODO(기준선): 촬영자 확인
- 5분 초과 간격 묶음이 실제 **촬영 Session**인지
- 25장이 **한 번의 세팅**인지

→ 확인 전까지 그룹은 **"시간 기반 추정 그룹"**으로 부르고, Session이라고 쓰지 않는다.

### 2-3. 추정 그룹 규칙 (v0)
1. 촬영 시각 순 정렬
2. 5분 초과 간격에서 끊음 (TODO(기준선): 경계값)
3. 끊은 묶음 안을 시간순 25장 블록으로 나눔 (TODO(기준선): 25장 가설)
4. 25장 미만 조각은 같은 날짜의 직전 블록에 붙임
- 결과: **34개 그룹** (25장 29개, 26~48장 5개)

Manifest에 추가할 열

| 열 | 값 예시 | 설명 |
|---|---|---|
| `capture_time` | 2025-04-10 14:44:03.911987 | 파일명에서 추출 |
| `capture_group` | `T04_B02` | 추정 그룹 ID |
| `group_basis` | `time_estimated` | 확인 후 `time_confirmed` / `visual` / `manual` 로 변경 |

### 2-4. 기존 validation 검토 근거
- 기존 validation 180장은 **전부 Dataset 2**
- `source_dataset` 1·2, `original_split` train·validation이 같은 시간대에 섞여 있음
- validation 180장 중 **135장은 60초 안에 찍힌 train 사진이 바로 옆에 있음** (중앙값 45초)
- → 연속 사진이 비슷하다면 기존 validation 점수는 실제보다 높게 나옴

---

## 3. Data Leakage 점검

| 항목 | 확인 방법 | 현재 결과 | 상태 |
|---|---|---|---|
| 완전히 동일한 파일 | 파일 해시(MD5) | 미실행 (이미지 파일 필요) | TODO |
| 파일명만 다른 동일 이미지 | 파일 해시 + 이미지 해시(pHash) | 미실행 | TODO |
| 시간상 매우 가까운 연속 촬영 | 파일명 시각 간격 | 1초 미만 1쌍: `250513_021405809512` / `250513_021406217768` (같은 그룹) | 육안 확인 |
| 거의 같은 장면 | 그룹 경계 앞뒤 육안 + pHash 거리 | 미실행 | TODO |
| 같은 원본에서 파생된 변형 | 증강·크롭 파일이 섞였는지 확인 | 파일명 패턴이 모두 원본 형식 → 파생본 흔적 없음 | 촬영자 확인 |

- 해시가 같은 이미지는 같은 그룹으로 합친다 (현재 `split_builder.py` 동작)
- TODO(기준선): pHash 거리 기준값 (예: 5 이하 = 거의 같은 장면)

---

## 4. Class × scene_type 분포

**Class 분포 = 무엇을 학습하는가 / scene_type 분포 = 어떤 장면에서 학습하는가.**
두 가지를 따로 보지 않고 **교차표**로 본다.

### 4-1. scene_type (확인됨)
| scene_type | 장수 | 촬영일 |
|---|---|---|
| kimchi_with_target | 725 | 04-10, 04-11, 04-24 |
| object_only | 151 | 05-13 (150) + 04-10 (1) |
| normal_kimchi | 24 | 04-10 오후 (2개 그룹에 섞여 있음) |

- 날짜와 scene_type이 거의 일치 → 날짜 단위로 떼면 scene_type 하나가 통째로 빠짐

### 4-2. Class × scene_type 교차표
출처: `labels/*.txt` 900개. 표기 = **객체 수 (포함 이미지 수)**

| Class | kimchi_with_target | object_only | normal_kimchi | 합계 | 포함 그룹 수 |
|---|---|---|---|---|---|
| 0 | 648 (241) | 61 (44) | 0 | 709 (285) | 23 |
| 1 | 1502 (451) | 163 (97) | 0 | 1665 (548) | 28 |
| 2 | 801 (297) | 136 (75) | 0 | 937 (372) | 26 |
| 3 | 289 (150) | 89 (46) | 0 | 378 (196) | 20 |
| 4 | 0 | 0 | 0 | 0 | 0 |
| 5 | 465 (240) | 0 | 0 | 465 (240) | 26 |
| 6 | 251 (52) | 0 | 0 | 251 (52) | **4** |

라벨 점검 결과
- TXT 900개 = Manifest 900행, 형식 오류 0건 (5칸, 좌표 0~1, 너비·높이 > 0)
- 줄 수 = `final_bbox_count`, Class 종류 수 = `final_class_count` 모두 일치

발견한 것
- **Class 4 = 0개**: 교과 7에서 고무장갑을 Class 1로 합친 결정과 일치 → 학습 Class에서 제외 여부 확인 필요 (data.yaml)
- **Class 5·6은 kimchi_with_target에만 있음**
- **Class 6이 Split의 병목**: 52장 중 50장이 `T00_B00`(25장) + `T00_B01`(25장, Train 고정 후보)에 몰림
  - `T00_B00`을 Test에 넣으면 Train의 Class 6은 `T00_B01` 25장 + 2장뿐
  - Val·Test 둘 다에 Class 6을 넣을 수 없음 (그룹이 사실상 2개)
  - TODO(기준선): Class 6을 Val과 Test 중 어디에 둘지, 또는 Class 6만 그룹 안에서 나누는 예외를 둘지
- **같은 25장 블록 안 사진은 같은 Class 구성을 공유하는 경우가 많음** (예: `T12_B01`은 25장 모두 Class 0 포함)
  → "25장 = 한 번의 세팅" 가설을 뒷받침하는 근거 (육안 확인으로 최종 판단)
- 빈 라벨 26장 중 25장이 normal_kimchi 그룹 2개(`T00_B01`, `T03_B00`)에 있음
  → 둘 다 Train에 두면 Val·Test에 "이물 없는 김치"가 거의 없어 오검출 평가가 어려움

### 4-3. 이 표로 답할 질문
- 각 Class가 충분한가? (예: Class 2 나뭇가지)
- 그 Class가 object_only에만 몰려 있지 않은가?
- kimchi_with_target에도 충분히 있는가? (실제 검출 상황은 김치 위)
- Val·Frozen Test에 각 Class가 kimchi_with_target 장면으로 들어가 있는가?
- TODO(기준선): 역할별 Class 최소 객체 수 N

---

## 5. 배정 절차

```
Manifest 읽기
→ capture_time / capture_group 추가 (추정)
→ 누수 점검 (해시 → 시간 → pHash)
→ Bridge Holdout 분리        (그룹 6개, 150장)
→ Frozen Test 분리 (Pool에서) (그룹 3개, 75장)
→ Validation 분리             (그룹 3개, 75장)
→ Train = 나머지              (그룹 22개, 600장)
→ Class × scene_type 분포 확인 → 조건 미달 시 seed만 바꿔 재선택
```

층화 조건
- object_only 그룹 6개 → Train 3 / Val 1 / Test 1 / Bridge 1
- Val·Test: object_only 1개 + kimchi_with_target 2개 (서로 다른 날짜)
- Bridge: object_only 1개 + kimchi_with_target 5개
- Val·Test·Bridge 각각 Class 0·1·2·3·5가 5장 이상 포함
- 크기가 25장이 아닌 그룹(26~48장)은 Train에 둔다
- 선택은 조건을 만족하는 조합 중 가장 작은 seed (재현 가능)

### 5-1. 조건을 만족하는 배정 후보 (seed 4)

| 역할 | 그룹 (촬영일) | Class 포함 이미지 수 [0,1,2,3,4,5,6] |
|---|---|---|
| Validation | T17_B03 (05-13 obj), T09_B00 (04-11), T12_B02 (04-24) | [40, 72, 34, 25, 0, 21, 0] |
| Frozen Test | T17_B05 (05-13 obj), T11_B00 (04-24), T09_B01 (04-11) | [10, 49, 11, 7, 0, 35, 0] |
| Bridge Holdout | T17_B04 (05-13 obj), T13_B01, T14_B01, T14_B00, T10_B01, T16_B01 (모두 04-24) | [66, 96, 110, 41, 0, 49, 1] |
| Train | 나머지 22개 그룹 | [169, 331, 217, 123, 0, 135, 51] |

이 후보의 한계 (팀 결정 필요)
- **Class 6: Val·Test에 0장** → Class 6 성능을 평가할 수 없음
  - 대안: 04-10 그룹 `T00_B00`(Class 6 25장)을 Test에 넣기 → Train의 Class 6은 26장으로 줄어듦
  - TODO(기준선): Class 6을 평가에서 볼지, 학습에 몰아줄지
- **빈 라벨(normal_kimchi) 25장 모두 Train** → Val·Test에서 오검출(이물 없는데 검출)을 볼 수 없음
  - TODO(기준선): normal_kimchi 그룹(36·39장)을 Train에 둘지 — 옮기면 Val·Test 수량이 75장에서 벗어남
- **Bridge 6개 중 kimchi 5개가 모두 04-24**
  - TODO(기준선): Bridge 성격(후보 A 최근 / 후보 B 날짜 분산)에 맞춰 조건 추가

> `split_builder.py`는 현재 Train → Val → Test → Bridge 순서로 채운다.
> 이 정책에 맞춰 **Bridge → Test → Val → Train** 순서로 바꿀 예정.

---

## 6. 확정 전 육안 확인 (6장 안팎)

| # | 확인할 것 | 볼 사진 | 판단에 쓰이는 곳 |
|---|---|---|---|
| 1 | 0.4초 간격 쌍이 같은 사진인가 | `250513_021405809512`, `250513_021406217768` | 3장 누수 |
| 2 | 연속 2장의 김치 배치가 같은가 | 아무 그룹의 연속 2장 | 그룹 크기 |
| 3 | 25장 경계 앞뒤 배치가 달라지는가 | 블록 경계 앞뒤 1장씩 | 25장 가설 |
| 4 | 5분 경계 앞뒤 배치가 달라지는가 | 묶음 경계 앞뒤 1장씩 | 경계값 |

판단
- 2 = 다름 → 연속 사진이 독립적 → 그룹을 더 작게 해도 됨 (현재 25장 블록이 더 보수적이므로 유지 가능)
- 2 = 같음, 3 = 다름 → 25장 블록 확정
- 2 = 같음, 3 = 같음 → 5분 묶음 단위로 변경 (object_only 처리 재검토)

---

## 7. 기록 항목 (split_report.md)

Split 정책 버전 / Dataset Version / 그룹 기준(`group_basis`) /
Train·Validation·Frozen Test·Bridge Holdout 수량 /
Class 분포 / scene_type 분포 / Class × scene_type 교차표 / 누수 점검 결과

---

## 8. TODO 요약

| 항목 | 위치 |
|---|---|
| 파일명 시각 = 캡처 시각 확인 | 촬영자 |
| 5분 경계값, 25장 가설 | 6장 육안 확인 → `group_candidates.py` |
| Bridge Holdout 성격 | 교과 14 목적 → `decide_bridge()` |
| normal_kimchi Test 포함 | `decide_test()` |
| Class 최소 객체 수 N | `check_distribution()` |
| pHash 거리 기준 | `build_groups()` |
| 배정 순서 변경 (Bridge 먼저) | `apply_split_policy()` |
| Manifest 열 이름 맞추기, `--root` 옵션 | `COL`, `read_manifest()` |
| Dataset Version 이름 | `DATASET_VERSION` |
| Class 6 배치 (그룹 2개뿐) | `decide_val()`, `decide_test()` |
| Class 4 학습 Class 제외 여부 | data.yaml |

---

## 9. 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v0 (초안) | 2026-10-14 | FINAL Manifest 시간 분석 + 가이드 15.2~15.4 반영 |
| v0.1 | 2026-10-14 | labels 900개로 Class × scene_type 교차표 작성, Class 6 병목 기록 |
| v0.2 | 2026-10-14 | 수량 확정 600/75/75/150, 기존 validation 미사용 확정, 배정 후보(seed 4) 추가 |