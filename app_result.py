import os
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk


#0. 설정값
CLASS_NAMES = [
  "나뭇잎·종이류",
  "플라스틱류·돌·금속류",
  "나뭇가지류",
  "벌레류",
  "고무장갑 (사용 안 함)",
  "병해·갈변",
  "파·고추"
]

CLASS_COLORS = [
  "#1aa84a",
  "#e53935",
  "#1e63d6",
  "#9c27b0",
  "#888888",
  "#f28c00",
  "#0b7a2e"
]

CLASS_LABELS = [f"{i} {name}" for i, name in enumerate(CLASS_NAMES)]

CANVAS_W = 760
CANVAS_H = 480
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp")
CSV_NAME = "label_status.csv"


#1. 프로그램 상태 (전역 변수)
image_paths = []       # 이미지 파일 경로 목록
current_index = -1     # 지금 보고 있는 이미지 번호
current_image = None   # 원본 이미지 (PIL)
photo_image = None     # Canvas에 표시하는 이미지 (참조를 유지해야 사라지지 않음)

scale = 1.0            # 원본 -> 화면 축소 비율
offset_x = 0           # Canvas 안에서 이미지가 시작되는 위치
offset_y = 0

boxes = []             # [class_id, x1, y1, x2, y2] (원본 이미지 픽셀 좌표)
meta_store = {}        # 파일명 -> 상태/Scene/메모
saved_names = set()    # 저장한 적 있는 파일명

start_x = 0
start_y = 0
temp_rect = None
dirty = False          # 저장하지 않은 변경이 있는지


#2. 좌표 변환
def canvas_to_image(cx, cy):
  """
  Canvas 좌표 -> 원본 이미지 좌표
  화면에는 이미지를 줄여서 보여주기 때문에
  저장할 때는 원본 기준 좌표로 바꿔야 합니다.
  """
  iw, ih = current_image.size
  ix = (cx - offset_x) / scale
  iy = (cy - offset_y) / scale

  ix = max(0, min(iw, ix))
  iy = max(0, min(ih, iy))
  return ix, iy


def image_to_canvas(ix, iy):
  """
  원본 이미지 좌표 -> Canvas 좌표
  """
  return ix * scale + offset_x, iy * scale + offset_y


def current_class_id():
  text = class_var.get()
  if text == "":
    return 0
  return int(text.split()[0])


def class_color(class_id):
  if 0 <= class_id < len(CLASS_COLORS):
    return CLASS_COLORS[class_id]
  return "black"


def class_name(class_id):
  if 0 <= class_id < len(CLASS_NAMES):
    return CLASS_NAMES[class_id]
  return "?"


#3. 화면 갱신
def get_selected_index():
  selected = tree.selection()
  if not selected:
    return -1
  return tree.index(selected[0])


def redraw_canvas():
  canvas.delete("all")

  if photo_image is not None:
    canvas.create_image(
      offset_x,
      offset_y,
      image=photo_image,
      anchor="nw"
    )

  selected = get_selected_index()

  for i, box in enumerate(boxes):
    class_id, x1, y1, x2, y2 = box
    cx1, cy1 = image_to_canvas(x1, y1)
    cx2, cy2 = image_to_canvas(x2, y2)
    color = class_color(class_id)

    canvas.create_rectangle(
      cx1,
      cy1,
      cx2,
      cy2,
      outline=color,
      width=4 if i == selected else 2
    )
    canvas.create_text(
      cx1 + 3,
      max(cy1 - 9, 8),
      text=f"{class_id} {class_name(class_id)}",
      fill=color,
      anchor="w",
      font=("Arial", 10, "bold")
    )


def refresh_tree():
  tree.delete(*tree.get_children())

  for i, box in enumerate(boxes):
    class_id, x1, y1, x2, y2 = box
    tree.insert(
      "",
      "end",
      iid=str(i),
      values=(
        i + 1,
        f"{class_id} {class_name(class_id)}",
        f"[{int(x1)}, {int(y1)}, {int(x2 - x1)}, {int(y2 - y1)}]"
      )
    )

  count_label.config(text=f"라벨 목록 ({len(boxes)}개)")


def update_info():
  if current_index < 0:
    return

  name = os.path.basename(image_paths[current_index])
  file_info_label.config(text=f"파일 이름 : {name}")
  progress_label.config(
    text=f"진행률 {current_index + 1} / {len(image_paths)}"
  )


def refresh_all():
  redraw_canvas()
  refresh_tree()
  update_info()


#4. 마우스 이벤트 (예제3)
def on_mouse_down(event):
  global start_x, start_y, temp_rect

  if current_image is None:
    return

  start_x = event.x
  start_y = event.y

  temp_rect = canvas.create_rectangle(
    start_x,
    start_y,
    start_x,
    start_y,
    outline=class_color(current_class_id()),
    width=2,
    dash=(4, 2)
  )


def on_mouse_drag(event):
  if temp_rect is None:
    return

  canvas.coords(
    temp_rect,
    start_x,
    start_y,
    event.x,
    event.y
  )


def on_mouse_up(event):
  global temp_rect, dirty

  if temp_rect is None:
    return

  canvas.delete(temp_rect)
  temp_rect = None

  ix1, iy1 = canvas_to_image(start_x, start_y)
  ix2, iy2 = canvas_to_image(event.x, event.y)

  #어느 방향으로 드래그해도 되도록 min, max로 정리합니다.
  x1 = min(ix1, ix2)
  y1 = min(iy1, iy2)
  x2 = max(ix1, ix2)
  y2 = max(iy1, iy2)

  if (x2 - x1) < 5 or (y2 - y1) < 5:
    status_label.config(text="BBox가 너무 작아서 추가하지 않았습니다.")
    return

  boxes.append([current_class_id(), x1, y1, x2, y2])
  dirty = True

  refresh_all()
  status_label.config(
    text=f"BBox 추가: ({int(x1)}, {int(y1)}) ~ ({int(x2)}, {int(y2)})"
  )


#5. 클래스 선택
def on_combo_select(event):
  class_listbox.selection_clear(0, tk.END)
  class_listbox.selection_set(current_class_id())


def on_list_select(event):
  selected = class_listbox.curselection()
  if selected:
    class_var.set(CLASS_LABELS[selected[0]])


#6. BBox 삭제 / Undo
def delete_selected():
  global dirty

  index = get_selected_index()
  if index == -1:
    status_label.config(text="목록에서 삭제할 BBox를 먼저 선택하세요.")
    return

  boxes.pop(index)
  dirty = True
  refresh_all()
  status_label.config(text="선택한 BBox를 삭제했습니다.")


def undo_last():
  global dirty

  if not boxes:
    status_label.config(text="되돌릴 BBox가 없습니다.")
    return

  boxes.pop()
  dirty = True
  refresh_all()
  status_label.config(text="마지막 BBox를 되돌렸습니다.")


#7. 상태 / Scene / 메모 (이미지마다 따로 보관)
def save_meta_to_memory():
  if current_index < 0:
    return

  name = os.path.basename(image_paths[current_index])
  meta = meta_store.setdefault(name, {})
  meta["status"] = status_var.get()
  meta["scene"] = scene_var.get()
  meta["note"] = note_text.get("1.0", tk.END).strip()


def load_meta_to_widgets():
  name = os.path.basename(image_paths[current_index])
  meta = meta_store.get(name, {})

  status_var.set(meta.get("status", "PASS"))
  scene_var.set(meta.get("scene", "kimchi_with_target"))
  note_text.delete("1.0", tk.END)
  note_text.insert("1.0", meta.get("note", ""))


#8. 이미지 불러오기
def load_boxes(path):
  """
  이미지와 같은 이름의 txt가 있으면 BBox를 읽어옵니다.
  (class cx cy w h, 0~1 비율 좌표)
  """
  txt_path = os.path.splitext(path)[0] + ".txt"
  result = []

  if not os.path.exists(txt_path):
    return result

  iw, ih = current_image.size

  with open(txt_path, "r", encoding="utf-8") as f:
    for line in f:
      parts = line.split()
      if len(parts) != 5:
        continue

      try:
        class_id = int(parts[0])
        cx, cy, w, h = map(float, parts[1:])
      except ValueError:
        continue

      x1 = (cx - w / 2) * iw
      y1 = (cy - h / 2) * ih
      x2 = (cx + w / 2) * iw
      y2 = (cy + h / 2) * ih
      result.append([class_id, x1, y1, x2, y2])

  return result


def show_image(index):
  global current_index, current_image, photo_image
  global scale, offset_x, offset_y, dirty

  if index < 0 or index >= len(image_paths):
    return

  #떠나기 전에 현재 이미지의 상태/메모를 보관합니다.
  save_meta_to_memory()

  current_index = index
  path = image_paths[index]
  current_image = Image.open(path)

  iw, ih = current_image.size
  scale = min(CANVAS_W / iw, CANVAS_H / ih)

  new_w = int(iw * scale)
  new_h = int(ih * scale)

  resized = current_image.resize((new_w, new_h))
  photo_image = ImageTk.PhotoImage(resized)

  offset_x = (CANVAS_W - new_w) // 2
  offset_y = (CANVAS_H - new_h) // 2

  boxes.clear()
  boxes.extend(load_boxes(path))
  dirty = False

  load_meta_to_widgets()
  refresh_all()
  status_label.config(text="흰색 영역에서 마우스를 드래그해 BBox를 그리세요.")


def load_csv(folder):
  csv_path = os.path.join(folder, CSV_NAME)
  if not os.path.exists(csv_path):
    return

  with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
      name = row.get("image_name", "")
      if name == "":
        continue

      try:
        box_count = int(row.get("box_count") or 0)
      except ValueError:
        box_count = 0

      meta_store[name] = {
        "status": row.get("status", "PASS"),
        "scene": row.get("scene_type", "kimchi_with_target"),
        "note": row.get("issue_note", ""),
        "box_count": box_count
      }
      saved_names.add(name)

      if worker_var.get() == "":
        worker_var.set(row.get("assignee", ""))
      if checker_var.get() == "":
        checker_var.set(row.get("reviewer", ""))


def confirm_leave():
  """
  저장하지 않은 변경이 있으면 이동 전에 물어봅니다.
  """
  if dirty and warn_var.get():
    return messagebox.askyesno(
      "미저장 경고",
      "저장하지 않은 BBox 변경이 있습니다.\n그냥 이동할까요?"
    )
  return True


def open_folder():
  global current_index

  if not confirm_leave():
    return

  folder = filedialog.askdirectory(title="이미지 폴더 선택")
  if folder == "":
    return

  files = sorted(
    f for f in os.listdir(folder)
    if f.lower().endswith(IMAGE_EXTS)
  )

  if not files:
    messagebox.showinfo("폴더 열기", "이미지 파일이 없는 폴더입니다.")
    return

  image_paths.clear()
  image_paths.extend(os.path.join(folder, f) for f in files)

  meta_store.clear()
  saved_names.clear()
  current_index = -1

  load_csv(folder)
  show_image(0)


def go_prev():
  if current_index > 0 and confirm_leave():
    show_image(current_index - 1)


def go_next():
  if 0 <= current_index < len(image_paths) - 1 and confirm_leave():
    show_image(current_index + 1)


#9. 저장 (TXT + CSV)
def write_csv():
  folder = os.path.dirname(image_paths[0])
  csv_path = os.path.join(folder, CSV_NAME)

  with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
      "image_name", "status", "assignee", "reviewer",
      "scene_type", "issue_note", "box_count"
    ])

    for path in image_paths:
      name = os.path.basename(path)
      if name not in saved_names:
        continue

      meta = meta_store.get(name, {})
      writer.writerow([
        name,
        meta.get("status", "PASS"),
        worker_var.get(),
        checker_var.get(),
        meta.get("scene", "kimchi_with_target"),
        meta.get("note", ""),
        meta.get("box_count", 0)
      ])


def save_current():
  global dirty

  if current_image is None:
    messagebox.showwarning("저장", "먼저 폴더를 열어 이미지를 불러오세요.")
    return False

  path = image_paths[current_index]
  name = os.path.basename(path)
  iw, ih = current_image.size

  #BBox를 0~1 비율 좌표(class cx cy w h)로 바꿔 txt에 저장합니다.
  txt_path = os.path.splitext(path)[0] + ".txt"
  with open(txt_path, "w", encoding="utf-8") as f:
    for class_id, x1, y1, x2, y2 in boxes:
      cx = (x1 + x2) / 2 / iw
      cy = (y1 + y2) / 2 / ih
      w = (x2 - x1) / iw
      h = (y2 - y1) / ih
      f.write(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

  save_meta_to_memory()
  meta_store[name]["box_count"] = len(boxes)
  saved_names.add(name)
  write_csv()

  dirty = False
  status_label.config(text=f"저장 완료: {name} (BBox {len(boxes)}개)")
  return True


def save_and_next():
  if save_current():
    go_next()


#10. Validation
def run_validation():
  if current_image is None:
    messagebox.showwarning("Validation", "먼저 폴더를 열어 이미지를 불러오세요.")
    return

  iw, ih = current_image.size
  problems = []

  for i, box in enumerate(boxes, start=1):
    class_id, x1, y1, x2, y2 = box

    if not 0 <= class_id < len(CLASS_NAMES):
      problems.append(f"BBox {i}: Class ID가 범위(0~6)를 벗어났습니다.")
    if x1 < 0 or y1 < 0 or x2 > iw or y2 > ih:
      problems.append(f"BBox {i}: 좌표가 이미지 밖으로 벗어났습니다.")
    if (x2 - x1) <= 0 or (y2 - y1) <= 0:
      problems.append(f"BBox {i}: 너비 또는 높이가 0입니다.")

  txt_path = os.path.splitext(image_paths[current_index])[0] + ".txt"
  if not os.path.exists(txt_path):
    problems.append("이 이미지의 TXT 파일이 아직 저장되지 않았습니다.")

  if problems:
    messagebox.showwarning("Validation 결과", "\n".join(problems))
  else:
    messagebox.showinfo(
      "Validation 결과",
      f"검사를 완료했습니다.\n문제가 없습니다. (BBox {len(boxes)}개)"
    )


#11. Window 생성
root = tk.Tk()
root.title("교과 7 - 조각김치 이물검출 라벨링 도구")
root.geometry("1200x740")


#12. GUI에서 사용할 변수
class_var = tk.StringVar(value=CLASS_LABELS[0])
status_var = tk.StringVar(value="PASS")
scene_var = tk.StringVar(value="kimchi_with_target")
worker_var = tk.StringVar()
checker_var = tk.StringVar()
warn_var = tk.BooleanVar(value=True)


#13. 상단 버튼 영역
toolbar = tk.Frame(root)
toolbar.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=8)

toolbar_buttons = [
  ("폴더 열기", open_folder),
  ("저장", save_current),
  ("저장 후 다음", save_and_next),
  ("← 이전", go_prev),
  ("다음 →", go_next),
  ("Undo", undo_last),
  ("Validation", run_validation)
]

for text, func in toolbar_buttons:
  tk.Button(
    toolbar,
    text=text,
    command=func,
    width=11,
    height=2
  ).pack(side="left", padx=3)


#14. 파일 정보 영역
info_frame = tk.Frame(root)
info_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10)

file_info_label = tk.Label(
  info_frame,
  text="파일 이름 : (폴더를 열어주세요)",
  font=("Arial", 11)
)
file_info_label.pack(side="left")

progress_label = tk.Label(
  info_frame,
  text="진행률 0 / 0",
  font=("Arial", 11)
)
progress_label.pack(side="right")


#15. 이미지 Canvas (왼쪽)
canvas = tk.Canvas(
  root,
  width=CANVAS_W,
  height=CANVAS_H,
  bg="white"
)
canvas.grid(row=2, column=0, padx=10, pady=8, sticky="n")

canvas.bind("<ButtonPress-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_drag)
canvas.bind("<ButtonRelease-1>", on_mouse_up)


#16. 오른쪽 패널
right_frame = tk.Frame(root)
right_frame.grid(row=2, column=1, padx=5, pady=8, sticky="n")

#16-1. 클래스 선택
class_frame = tk.LabelFrame(right_frame, text="클래스 선택")
class_frame.pack(fill="x", pady=3)

class_combo = ttk.Combobox(
  class_frame,
  textvariable=class_var,
  values=CLASS_LABELS,
  state="readonly",
  width=34
)
class_combo.pack(padx=8, pady=4)
class_combo.bind("<<ComboboxSelected>>", on_combo_select)

class_listbox = tk.Listbox(
  class_frame,
  height=7,
  exportselection=False,
  width=36
)
class_listbox.pack(padx=8, pady=4)

for i, label in enumerate(CLASS_LABELS):
  class_listbox.insert(tk.END, label)
  class_listbox.itemconfig(i, fg=CLASS_COLORS[i])

class_listbox.selection_set(0)
class_listbox.bind("<<ListboxSelect>>", on_list_select)

#16-2. 라벨 목록
list_frame = tk.LabelFrame(right_frame, text="라벨 목록")
list_frame.pack(fill="x", pady=3)

count_label = tk.Label(list_frame, text="라벨 목록 (0개)")
count_label.pack(anchor="w", padx=8)

tree = ttk.Treeview(
  list_frame,
  columns=("no", "class", "pos"),
  show="headings",
  height=5
)
tree.heading("no", text="No")
tree.heading("class", text="클래스")
tree.heading("pos", text="위치 (x, y, w, h)")
tree.column("no", width=35, anchor="center")
tree.column("class", width=130)
tree.column("pos", width=150)
tree.pack(padx=8, pady=2)
tree.bind("<<TreeviewSelect>>", lambda e: redraw_canvas())

tk.Button(
  list_frame,
  text="선택 삭제",
  command=delete_selected
).pack(pady=4)

#16-3. 검수 상태 + 작업자 정보
row1 = tk.Frame(right_frame)
row1.pack(fill="x", pady=3)

status_frame = tk.LabelFrame(row1, text="검수 상태")
status_frame.pack(side="left", fill="both", expand=True)

for value in ["PASS", "EDITED", "REVIEW", "REVIEWED"]:
  tk.Radiobutton(
    status_frame,
    text=value,
    variable=status_var,
    value=value
  ).pack(anchor="w", padx=8)

worker_frame = tk.LabelFrame(row1, text="작업자 정보")
worker_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

tk.Label(worker_frame, text="작업자 :").grid(row=0, column=0, padx=5, pady=8)
tk.Entry(worker_frame, textvariable=worker_var, width=8).grid(row=0, column=1)
tk.Label(worker_frame, text="검수자 :").grid(row=1, column=0, padx=5, pady=8)
tk.Entry(worker_frame, textvariable=checker_var, width=8).grid(row=1, column=1)

#16-4. Scene Type + Issue / Note
row2 = tk.Frame(right_frame)
row2.pack(fill="x", pady=3)

scene_frame = tk.LabelFrame(row2, text="Scene Type")
scene_frame.pack(side="left", fill="both", expand=True)

scene_options = [
  ("김치+대상", "kimchi_with_target"),
  ("정상 김치", "normal_kimchi"),
  ("객체 단독", "object_only"),
  ("기타 확인 필요", "need_check")
]

for text, value in scene_options:
  tk.Radiobutton(
    scene_frame,
    text=text,
    variable=scene_var,
    value=value
  ).pack(anchor="w", padx=8)

note_frame = tk.LabelFrame(row2, text="Issue / Note")
note_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

note_text = tk.Text(note_frame, width=18, height=6)
note_text.pack(padx=5, pady=4)

#16-5. 미저장 경고
tk.Checkbutton(
  right_frame,
  text="미저장 경고",
  variable=warn_var
).pack(anchor="w", pady=2)


#17. 하단 상태 Label
status_label = tk.Label(
  root,
  text="[폴더 열기]를 눌러 이미지 폴더를 선택하세요.",
  font=("Arial", 11),
  anchor="w"
)
status_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)


#18. GUI 실행
root.mainloop()