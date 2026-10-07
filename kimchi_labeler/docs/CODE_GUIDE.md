# 코드 설명서 (역할별)

> 원칙: **화면(GUI)과 데이터 로직(session)을 분리**했습니다. 그래서 GUI 를 띄우지 않고도 `tests/test_core.py` 로 저장·좌표·병합·FINAL 을 자동으로 시험할 수 있습니다.
> 발표 때도 "어떤 함수가 어떤 문제를 막는가"를 설명할 수 있어야 합니다.

```text
main.py
  └─ ui/ (app.py 화면·키 / menubar.py 메뉴 / panels.py 배치)
        ├─ bbox/canvas_editor.py (이미지·BBox 그리기, 마우스 편집)
        └─ bbox/session.py (Load · 편집 · Save · 상태규칙)
              ├─ yolo/yolo_io.py          (TXT ↔ Box, 안전저장)
              ├─ bbox/view.py             (원본 ↔ 화면 좌표)  ← ui 가 직접 사용
              ├─ yolo/dataset.py          (RAW 조사, 경로 규칙)
              ├─ manifest.py              (CSV 기록, 병합)
              └─ validation/validator.py  (자동 검사)
scripts/00~10 → 위 모듈을 조합한 운영 도구
```

---

## 1. PM / Integrator: `config.py`, `main.py`, `scripts/03_assign.py`, `scripts/07_build_final.py`

**config.py**: 팀 기준(Baseline)을 코드로 Freeze 한 파일입니다.

```python
CLASS_NAMES = {0: "나뭇잎·종이류", ..., 4: "고무장갑(미사용)", ..., 6: "파·고추"}
UNUSED_CLASS_IDS = {4}                       # 사용 안 함 -> REVIEW
ACTIVE_CLASS_IDS = [0, 1, 2, 3, 5, 6]        # 새 BBox 에 쓸 수 있는 Class
FINAL_READY_STATUSES = {"PASS", "REVIEWED"}  # FINAL 로 갈 수 있는 상태
```

- `Paths.check_not_same()` : RAW 와 WORK 가 같거나 하나가 다른 하나 안에 있으면 실행을 막습니다. RAW 를 보호하는 첫 번째 장치입니다.

**03_assign.py**: 배분 방법입니다.
- Dataset/split 그룹마다 "현재 가장 적게 받은 사람"에게 한 장씩 줍니다. 그래서 모두가 고르게 섞인 데이터를 받습니다.
- 검수자는 `workers[i+1]` 입니다 (A→B→…→F→A). 자기 작업을 자기가 검수할 수 없습니다.
- Pilot 은 (Dataset, split, 빈TXT / 단일 / 다중BBox) 버킷을 돌아가며 뽑습니다.

**07_build_final.py**: 다음 조건을 하나라도 어기면 FINAL 을 만들지 않습니다 (Gate 를 코드로 구현).
`FINAL 불가 상태 0` + `CRITICAL 0` + `RAW 해시 동일`

---

## 2. GUI / Image: `src/ui/`, `src/bbox/canvas_editor.py`

| 파일 | 하는 일 |
|---|---|
| `app.py` | 메인 창 `LabelApp`. 메뉴 구성, 단축키, 이미지 이동, 저장, 통계 메뉴 동작, `run()` |
| `panels.py` | 위젯 배치만 담당 (왼쪽 목록, 가운데 Canvas, 오른쪽 두 열, 아래 도구 막대) |
| `canvas_editor.py` | 이미지 그리기(피라미드, 보이는 영역만 crop)와 BBox 그리기·마우스 편집 |
| `menubar.py` | 직접 만든 메뉴 막대. 드롭다운은 메인 창 안의 Frame 이라 잔상이 없고, 항상 하나만 열립니다 |
| `dialogs.py` | Validation 결과 표, 진행현황, Class 통계, 단축키 안내 창 |
| `style.py` | 색, 글꼴, 상태 기호, 버튼/테두리 만드는 함수 |

| 부분 | 핵심 |
|---|---|
| `goto()` | 이동 전 `confirm_leave()` 로 저장 안 된 변경 확인 → `session.load()` → 이미지 피라미드 생성 → `fit()` |
| `make_pyramid()` | 4K 원본, 1/2, 1/4 크기를 미리 만들어 둡니다. 배율이 낮을 때는 작은 것을 써서 빠르게 그립니다 |
| `render()` | **보이는 영역만** 잘라서(crop) 확대/축소합니다. 4K 전체를 매번 리사이즈하지 않습니다 |
| `draw_boxes()` | Box(원본 좌표) → `view.to_canvas()` → 사각형. Class 별 색, 선택 시 굵게, Class 4 는 점선 |
| `bind_keys()` | Entry 에 글자를 입력할 때는 단축키를 무시합니다 (`guard`) |
| `on_left_down/drag/up()` | 모드(draw/select/pan)와 `drag` 딕셔너리로 그리기·이동·크기조절을 구분. 드래그 시작 때 1번만 Undo 지점 (`session.begin_edit`) |
| `hit_handle()` | 선택 BBox 의 8개 핸들 중 마우스 근처(7px) 핸들 찾기 |
| `apply_box_entries()` | 오른쪽 칸의 YOLO 좌표 → 픽셀 → `session.replace_box()` |
| `refresh_image_list()` | 왼쪽 목록을 Manifest 상태 색/기호로 다시 그림, 저장하면 해당 줄만 갱신 |
| 버튼 `takefocus=0` | 버튼이 포커스를 가져가 Space 가 버튼을 누르는 문제를 막습니다 |

이미지 전환 때 이전 BBox 가 남지 않는 이유: `session.load()` 가 `LoadedImage` 를 **새로 만들기** 때문입니다. 이전 상태를 고쳐 쓰지 않습니다.

### 메뉴 잔상 문제와 `menubar.py`

`tk.Menu` 로 만든 메뉴는 WSL(WSLg) 화면에서 한 메뉴를 연 채 다른 메뉴로 마우스를 옮기면 이전 드롭다운이 잔상으로 남았습니다.
`tk.Menu` 의 드롭다운은 메인 창과 별개인 작은 창인데, WSLg 가 그 창이 닫힌 자리를 제때 다시 그려 주지 않기 때문입니다. (드롭다운을 새 창으로 만들고 `destroy()` 해도 잔상이 남았습니다.)

- 드롭다운을 별도 창으로 만들지 않고, 메인 창 안에 `Frame` 을 `place()` 로 띄웠다가 `destroy()` 합니다. 메인 창이 직접 다시 그리므로 잔상이 생기지 않습니다.
- 다른 메뉴 제목에 마우스가 올라가면 열린 메뉴를 먼저 없애고 새 메뉴를 엽니다. 메뉴는 항상 하나만 열려 있습니다.
- 메뉴 바깥 클릭, `Esc`, 창 이동·최소화, 다른 프로그램으로 전환할 때도 닫힙니다.
- 메뉴가 열려 있을 때 바깥을 누르면 **메뉴만 닫히고** 그 클릭은 무시됩니다 (`CLICK_GUARD` bindtag). 메뉴를 닫으려다 이미지 목록이 바뀌거나 버튼이 눌리는 일을 막습니다.
- 옆 메뉴로 마우스를 옮겨 열린 메뉴를 바로 클릭해도 닫히지 않습니다 (`opened_by_hover`).
- 키보드: `Alt+F/V/T/Q/S/H`, `F10` 으로 열고 `↑↓←→`, `Enter`, `Esc` 로 움직입니다. 메뉴가 열려 있는 동안에는 A, D, Space 같은 단축키가 눌리지 않습니다.

---

## 3. BBox / Coordinate: `src/bbox/view.py`, `yolo_io.py` 의 변환 함수

```python
# 원본 → 화면
canvas_x = image_x * scale + offset_x
# 화면 → 원본
image_x = (canvas_x - offset_x) / scale
```

- **BBox 는 항상 원본 픽셀 좌표로 저장합니다.** 화면에 그릴 때만 변환하므로 Zoom/Pan 을 해도 실제 위치는 변하지 않습니다.
- `zoom_at(factor, cx, cy)` 는 마우스 아래 이미지 점을 먼저 구하고, 배율을 바꾼 뒤 그 점이 같은 화면 위치에 오도록 offset 을 다시 계산합니다.

```python
ix, iy = self.to_image(cx, cy)
self.scale = new_scale
self.offset_x = cx - ix * new_scale
```

- YOLO ↔ 픽셀 변환:

```python
x1 = (cx - w/2) * img_w ;  x2 = (cx + w/2) * img_w        # yolo_to_pixel
cx = (x1 + x2) / 2 / img_w ;  w = (x2 - x1) / img_w        # pixel_to_yolo
```

- `Box.clamp()` 는 이미지 밖으로 나간 부분을 잘라냅니다. `MIN_BOX_PX` 보다 작은 박스는 만들지 않습니다 (실수 드래그 방지).
- 검증: `09_golden_test.py` 가 여러 Zoom/Pan 상태에서 왕복 오차 < 1e-6 인지 확인합니다.

---

## 4. Label / Storage: `src/yolo/yolo_io.py`, `src/bbox/session.py`

**파싱** `parse_line()` 은 값 5개, 숫자 변환, class 정수 여부를 확인하고 실패하면 오류 메시지를 돌려줍니다. 자동으로 고치지 않습니다.

**안전저장** `atomic_write_text()`

```python
fd, tmp = tempfile.mkstemp(dir=path.parent)   # 같은 폴더에 임시파일
write(tmp) -> os.replace(tmp, path)            # 한 번에 교체 -> 중간에 꺼져도 TXT 안 깨짐
```

**저장 규칙** `LabelSession.save()`

1. WORK 경로가 RAW 안이면 즉시 중단합니다.
2. `changed_vs_raw()` 가 참인데 PASS 를 요청하면 → EDITED 로 바꿉니다.
3. 라벨이 RAW 와 같으면 RAW 원문을 **그대로 복사**합니다 (소수점 형식까지 보존).
4. Manifest 에 status, final_bbox_count, scene_type, note, 작업자, 시간을 기록합니다.

**경로 규칙** `dataset.image_rel_to_label_rel()`
`.../images/train/a.jpg` → `.../labels/train/a.txt`. 키는 **파일명이 아니라 RAW 기준 상대경로**입니다 (Dataset1 과 2 에 같은 파일명이 있어도 안전).

---

## 5. QA / Validation: `src/validation/validator.py`, `scripts/02`, `06`, `09`, `00`

| 코드 | 심각도 | 의미 |
|---|---|---|
| PAIR_NO_TXT / PAIR_NO_JPG | CRITICAL | 짝 없음 |
| PARSE | CRITICAL | 값 개수나 숫자 형식 오류 |
| CLASS_RANGE | CRITICAL | 0~6 밖 |
| COORD_RANGE / WH_ZERO / BOX_OUTSIDE | CRITICAL | 좌표 범위·경계 오류 |
| IMAGE_READ | CRITICAL | 이미지가 안 열림 |
| CLASS_4 | REVIEW | 미사용 Class |
| DUPLICATE | REVIEW | 같은 Class 이고 IoU ≥ 0.9 |
| TINY_BOX | REVIEW | 3px 미만 |
| EXIF_ROTATE | REVIEW | 사진 회전 정보가 있어 좌표가 어긋날 수 있음 |
| EMPTY_LABEL | INFO | BBox 0개 (정상 이미지인지 사람이 확인) |

- `image_size()` 는 이미지 헤더만 읽어서 900장도 빠르게 검사합니다.
- `00_raw_snapshot.py` 는 SHA-256 으로 RAW 가 1바이트라도 바뀌었는지 확인합니다.
- `06_pass_sample.py` 는 PASS 중 절반을 위험도(작은 BBox, BBox 수, 희소 Class) 순으로, 절반을 무작위로 뽑습니다.

---

## 6. Data / Document: `src/manifest.py`, `manifest_builder.py`, `stats.py`, `scripts/01`, `04`, `05`, `08`

- Manifest 는 `utf-8-sig` 로 저장해서 엑셀에서 한글이 깨지지 않습니다.
- **병합** `merge_manifests()`: 같은 이미지는 `updated_at` 이 최신인 행을 씁니다. 시각이 같으면 사람이 작업한 행이 우선입니다. 라벨 파일도 그 행을 쓴 사람의 WORK 에서 가져옵니다.
- `04_merge.py` 는 담당/검수자가 아닌 사람이 수정했거나, REVIEWED 이후 다시 수정된 경우를 `reports/merge_conflicts.csv` 에 남깁니다.
- `stats.diff_boxes()`: RAW 와 최종 BBox 를 IoU 0.5 이상으로 짝지어 **유지 / 위치수정 / Class변경 / 추가 / 삭제** 수를 셉니다. QA Summary 와 Handoff 의 핵심 숫자입니다.

---

## 7. 하루 마감 루틴 (모든 PC 공통)

```text
각자: 프로그램 종료(저장 확인) → 자기 data/work 폴더를 공유폴더 work_<이름> 으로 복사
Data: python scripts/04_merge.py --inputs work_A ... work_F --out work_merged_1014
QA  : python scripts/02_validate.py --work work_merged_1014
      python scripts/00_raw_snapshot.py --verify
Doc : python scripts/05_qa_summary.py --work work_merged_1014
PM  : QA_Summary 확인 → 다음 날 아침 work_merged 를 모두에게 배포 (각자 data/work 로 교체)
```

## 8. 직접 고쳐보며 공부할 과제 (역할별 추천)

| 역할 | 과제 |
|---|---|
| GUI | 상태별 색으로 진행 위치 표시 / 썸네일 목록 |
| 좌표 | 방향키로 선택 BBox 1px 미세 이동 |
| 저장 | 저장 시 `.bak` 백업 1개 유지 옵션 |
| QA | Validation 결과를 심각도별로 필터링 |
| Data | scene_type 별 Class 분포 표를 QA Summary 에 추가 (`stats.scene_class` 사용) |
| PM | `tests/test_core.py` 에 새 테스트 1개씩 추가하는 규칙 운영 |

> Feature Freeze(10/13) 이후에는 위 과제를 본 작업 프로그램에 넣지 말고 **별도 브랜치**에서만 실습합니다.
