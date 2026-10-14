# Split 정책 (split_policy.md)

- 상태: **초안 v0** — 육안 확인(6장) 후 확정
- 작성일: 2026-10-14 / 작성: 교과 8 Data 담당
- 대상: 교과 7 FINAL Dataset 900장 (`manifest_final.csv`)
- 도구: `group_candidates.py` → `split_builder.py`
- 미확정 표시: `TODO(기준선)`

> **원칙: 비율보다 누수를 막고 역할을 고정하는 것이 더 중요하다.**

---

## 1. 역할별 정책

### Bridge Holdout
- 교과 8 Train / Validation / Frozen Test와 **가장 먼저, 별도로** 분리
- 교과 8 학습·튜닝·모델 선택에 사용하지 않음 (열어보지 않음)
- 교과 14 연결용으로 보존
- 수량 후보: 50장 (`capture_group` 2개)
- TODO(기준선): 교과 14에서 확인할 목적에 맞춰 그룹 선택
  - 후보 A: 가장 최근 kimchi_with_target 그룹 (시간상 새로운 데이터)
  - 후보 B: 날짜별 무작위 그룹 (Test와 같은 분포)

### Frozen Test
- Bridge를 뺀 **개발용 후보 Pool**에서 `capture_group` 단위로 별도 분리
- Final Model을 선택한 뒤 **마지막 평가에만** 사용
- 한 번 정하면 변경하지 않음 (변경 시 정책 버전을 올리고 사유 기록)
- 수량 후보: 100장 (그룹 4개)

### Validation
- 가이드 기준: 기존 Dataset 2 / validation을 우선 후보로 검토
- **검토 결과 (2-3 참고): 누수 위험이 있어 그대로 쓰기 어려움 → 조건부**
  - 육안 확인 결과 "연속 사진이 매번 다른 배치" → 기존 validation 180장 그대로 사용 가능
  - "연속 사진이 같은 배치" → `capture_group` 단위로 Pool에서 새로 분리 (125장, 그룹 5개)
- Baseline과 Improved 비교에 사용
- TODO(기준선): 육안 확인 후 위 둘 중 하나로 확정

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
- 결과: **34개 그룹** (25장 30개, 26~48장 4개)

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

### 4-2. Class × scene_type 교차표 (TXT 필요 — 미작성)
Manifest에는 Class 번호가 없어 TXT를 읽어 채운다. (객체 수 / 포함 이미지 수)

| Class | kimchi_with_target | object_only | normal_kimchi | 합계 |
|---|---|---|---|---|
| 0 | | | | |
| 1 | | | | |
| 2 | | | | |
| … | | | | |

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
→ Bridge Holdout 분리        (그룹 2개, ~50장)
→ Frozen Test 분리 (Pool에서) (그룹 4개, ~100장)
→ Validation 결정             (기존 180장 또는 그룹 5개 ~125장)
→ Train = 나머지
→ Class × scene_type 분포 확인 → 조건 미달 시 seed만 바꿔 재선택
```

층화 조건 (Frozen Test·Validation)
- object_only 그룹 1개씩 포함 (object_only는 그룹 6개: Train 4 / Val 1 / Test 1)
- kimchi_with_target 그룹은 04-10 / 04-11 / 04-24에서 고르게
- 빈 라벨(배경) 이미지 최소 1장 포함 (전체 26장)
- 4-3의 Class 조건 충족
- 크기가 25장이 아닌 그룹(26~48장)은 Train에 둔다
- TODO(기준선): normal_kimchi 그룹(36·39장, 2개)을 Test에 넣을지 — 현재 둘 다 Train
- 선택은 조건을 만족하는 조합 중 seed=42 (재현 가능)

> `split_builder.py`는 현재 Train → Val → Test → Bridge 순서로 채운다.
> 이 정책에 맞춰 **Bridge → Test → Val → Train** 순서로 바꿀 예정.

---

## 6. 확정 전 육안 확인 (6장 안팎)

| # | 확인할 것 | 볼 사진 | 판단에 쓰이는 곳 |
|---|---|---|---|
| 1 | 0.4초 간격 쌍이 같은 사진인가 | `250513_021405809512`, `250513_021406217768` | 3장 누수 |
| 2 | 연속 2장의 김치 배치가 같은가 | 아무 그룹의 연속 2장 | **1장 Validation 결정**, 그룹 크기 |
| 3 | 25장 경계 앞뒤 배치가 달라지는가 | 블록 경계 앞뒤 1장씩 | 25장 가설 |
| 4 | 5분 경계 앞뒤 배치가 달라지는가 | 묶음 경계 앞뒤 1장씩 | 경계값 |

판단
- 2 = 다름 → 연속 사진이 독립적 → 기존 validation 사용 가능, 그룹을 더 작게 해도 됨
- 2 = 같음, 3 = 다름 → 25장 블록 확정, Validation은 그룹 단위로 새로 분리
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
| 기존 validation 사용 여부 | 6장 #2 → `SPLIT_POLICY["keep_original_val"]` |
| Bridge Holdout 성격 | 교과 14 목적 → `decide_bridge()` |
| normal_kimchi Test 포함 | `decide_test()` |
| Class 최소 객체 수 N | `check_distribution()` |
| pHash 거리 기준 | `build_groups()` |
| 배정 순서 변경 (Bridge 먼저) | `apply_split_policy()` |
| Manifest 열 이름 맞추기, `--root` 옵션 | `COL`, `read_manifest()` |
| Dataset Version 이름 | `DATASET_VERSION` |

---

## 9. 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v0 (초안) | 2026-10-14 | FINAL Manifest 시간 분석 + 가이드 15.2~15.4 반영 |