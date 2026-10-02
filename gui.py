import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import csv

# ============================================================
# 클래스
# ============================================================

CLASS_NAMES = {
    0: '나뭇잎 · 종이류',
    1: '플라스틱 · 돌 · 금속',
    2: '나뭇가지류',
    3: '벌레류',
    4: '고무장갑',
    5: '병해 · 갈변',
    6: '파 · 고추',
}

CLASS_COLORS = {
    0: '#72D6A3',
    1: '#55B9E8',
    2: '#F2A65A',
    3: '#B979D1',
    4: '#E96B6B',
    5: '#E8C45B',
    6: '#4F9FE6',
}

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


# ============================================================
# YOLO TXT 읽기 / 저장
# ============================================================

def load_labels(txt_path):
    labels = []

    if not txt_path.exists():
        return labels

    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()

            if len(parts) != 5:
                continue

            try:
                labels.append({
                    'class_id': int(parts[0]),
                    'cx': float(parts[1]),
                    'cy': float(parts[2]),
                    'w': float(parts[3]),
                    'h': float(parts[4]),
                })
            except ValueError:
                continue

    return labels


def save_labels(txt_path, labels):
    with open(txt_path, 'w', encoding='utf-8') as f:
        for label in labels:
            f.write(
                f"{label['class_id']} "
                f"{label['cx']:.6f} "
                f"{label['cy']:.6f} "
                f"{label['w']:.6f} "
                f"{label['h']:.6f}\n"
            )


# ============================================================
# GUI
# ============================================================

class LabelingApp:
    def __init__(self, root):
        self.root = root
        self.root.title('YOLO Labeling Tool')
        self.root.geometry('1450x850')
        self.root.configure(bg='#0B1220')

        # 현재 선택한 이미지
        self.current_image = None

        # 같은 폴더의 이미지 목록
        self.images = []
        self.current_index = -1

        # 현재 라벨
        self.labels = []
        self.selected_label = None

        # 이미지
        self.original_image = None
        self.tk_image = None
        self.fit_scale = 1
        self.scale = 1
        self.offset_x = 0
        self.offset_y = 0

        # 수정 여부
        self.dirty = False

        # BBox 그리기
        self.draw_start = None
        self.temp_box = None

        # Pan
        self.pan_start = None

        self.setup_style()
        self.setup_ui()
        self.bind_keys()

    # ========================================================
    # Style
    # ========================================================

    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure(
            'TButton',
            font=('Segoe UI', 10),
            padding=(10, 7)
        )

        style.configure(
            'Small.TButton',
            font=('Segoe UI', 9),
            padding=(7, 5)
        )

    # ========================================================
    # UI
    # ========================================================

    def setup_ui(self):

        # ---------------- Header ----------------

        header = tk.Frame(
            self.root,
            bg='#0B1220',
            height=65
        )
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(
            header,
            text='YOLO LABELING',
            bg='#0B1220',
            fg='white',
            font=('Segoe UI Semibold', 17)
        ).pack(side='left', padx=20)

        self.file_name = tk.StringVar(value='이미지를 선택하세요')

        tk.Label(
            header,
            textvariable=self.file_name,
            bg='#0B1220',
            fg='#AAB3C5',
            font=('Segoe UI', 10)
        ).pack(side='left')

        ttk.Button(
            header,
            text='이미지 열기',
            command=self.open_image
        ).pack(side='right', padx=18, pady=13)

        # ---------------- Main ----------------

        main = tk.Frame(
            self.root,
            bg='#111827'
        )
        main.pack(fill='both', expand=True)

        # ---------------- Left ----------------

        left = tk.Frame(
            main,
            bg='#111827',
            width=240
        )
        left.pack(side='left', fill='y')
        left.pack_propagate(False)

        tk.Label(
            left,
            text='IMAGE LIST',
            bg='#111827',
            fg='#788399',
            font=('Segoe UI Semibold', 9)
        ).pack(anchor='w', padx=16, pady=(18, 8))

        self.image_list = tk.Listbox(
            left,
            bg='#172033',
            fg='#DCE2EC',
            selectbackground='#2563EB',
            selectforeground='white',
            relief='flat',
            highlightthickness=0,
            font=('Segoe UI', 9)
        )
        self.image_list.pack(
            fill='both',
            expand=True,
            padx=12,
            pady=5
        )

        self.image_list.bind(
            '<<ListboxSelect>>',
            self.list_selected
        )

        self.progress = tk.StringVar(value='0 / 0')

        tk.Label(
            left,
            textvariable=self.progress,
            bg='#111827',
            fg='#8792A6',
            font=('Segoe UI Semibold', 9)
        ).pack(pady=15)

        # ---------------- Center ----------------

        center = tk.Frame(
            main,
            bg='#0F172A'
        )
        center.pack(
            side='left',
            fill='both',
            expand=True
        )

        self.canvas = tk.Canvas(
            center,
            bg='#070C14',
            highlightthickness=0,
            cursor='crosshair'
        )
        self.canvas.pack(
            fill='both',
            expand=True,
            padx=12,
            pady=12
        )

        # 왼쪽 클릭 = BBox
        self.canvas.bind(
            '<ButtonPress-1>',
            self.mouse_down
        )
        self.canvas.bind(
            '<B1-Motion>',
            self.mouse_drag
        )
        self.canvas.bind(
            '<ButtonRelease-1>',
            self.mouse_up
        )

        # 오른쪽 클릭 = Pan
        self.canvas.bind(
            '<ButtonPress-3>',
            self.pan_down
        )
        self.canvas.bind(
            '<B3-Motion>',
            self.pan_drag
        )
        self.canvas.bind(
            '<ButtonRelease-3>',
            self.pan_up
        )

        bottom = tk.Frame(
            center,
            bg='#0F172A',
            height=55
        )
        bottom.pack(fill='x')
        bottom.pack_propagate(False)

        ttk.Button(
            bottom,
            text='← 이전',
            command=self.previous_image
        ).pack(side='left', padx=(15, 5), pady=9)

        ttk.Button(
            bottom,
            text='다음 →',
            command=self.next_image
        ).pack(side='left', padx=5, pady=9)

        ttk.Button(
            bottom,
            text='Fit',
            style='Small.TButton',
            command=self.fit_image
        ).pack(side='right', padx=3, pady=9)

        ttk.Button(
            bottom,
            text='−',
            style='Small.TButton',
            command=lambda: self.zoom(0.8)
        ).pack(side='right', padx=3, pady=9)

        ttk.Button(
            bottom,
            text='+',
            style='Small.TButton',
            command=lambda: self.zoom(1.25)
        ).pack(side='right', padx=3, pady=9)

        # ---------------- Right ----------------

        right = tk.Frame(
            main,
            bg='#111827',
            width=310
        )
        right.pack(side='right', fill='y')
        right.pack_propagate(False)

        tk.Label(
            right,
            text='ANNOTATION',
            bg='#111827',
            fg='#788399',
            font=('Segoe UI Semibold', 9)
        ).pack(anchor='w', padx=16, pady=(18, 8))

        self.object_list = tk.Listbox(
            right,
            height=11,
            bg='#172033',
            fg='#DCE2EC',
            selectbackground='#2563EB',
            selectforeground='white',
            relief='flat',
            highlightthickness=0,
            font=('Segoe UI', 9)
        )
        self.object_list.pack(
            fill='x',
            padx=15
        )

        self.object_list.bind(
            '<<ListboxSelect>>',
            self.object_selected
        )

        object_buttons = tk.Frame(
            right,
            bg='#111827'
        )
        object_buttons.pack(
            fill='x',
            padx=15,
            pady=8
        )

        ttk.Button(
            object_buttons,
            text='+ BBox',
            style='Small.TButton',
            command=self.add_bbox_message
        ).pack(side='left')

        ttk.Button(
            object_buttons,
            text='삭제',
            style='Small.TButton',
            command=self.delete_selected
        ).pack(side='left', padx=5)

        tk.Label(
            right,
            text='CLASS',
            bg='#111827',
            fg='#8792A6',
            font=('Segoe UI Semibold', 9)
        ).pack(anchor='w', padx=16, pady=(8, 5))

        self.class_var = tk.StringVar()

        self.class_combo = ttk.Combobox(
            right,
            state='readonly',
            textvariable=self.class_var,
            values=[
                f'{i} · {CLASS_NAMES[i]}'
                for i in range(7)
            ]
        )
        self.class_combo.pack(
            fill='x',
            padx=15
        )

        self.class_combo.bind(
            '<<ComboboxSelected>>',
            self.change_class
        )

        # Class Guide

        tk.Label(
            right,
            text='CLASS GUIDE',
            bg='#111827',
            fg='#8792A6',
            font=('Segoe UI Semibold', 9)
        ).pack(anchor='w', padx=16, pady=(18, 6))

        guide = tk.Frame(
            right,
            bg='#172033'
        )
        guide.pack(
            fill='x',
            padx=15
        )

        for class_id in range(7):
            row = tk.Frame(
                guide,
                bg='#172033'
            )
            row.pack(
                fill='x',
                padx=8,
                pady=3
            )

            tk.Label(
                row,
                text='●',
                fg=CLASS_COLORS[class_id],
                bg='#172033',
                font=('Segoe UI', 10)
            ).pack(side='left')

            tk.Label(
                row,
                text=f'{class_id}  {CLASS_NAMES[class_id]}',
                fg='#DCE2EC',
                bg='#172033',
                font=('Segoe UI', 8)
            ).pack(side='left', padx=5)

        # ---------------- Save ----------------

        save_frame = tk.Frame(
            right,
            bg='#111827'
        )
        save_frame.pack(
            side='bottom',
            fill='x',
            padx=15,
            pady=15
        )

        ttk.Button(
            save_frame,
            text='저장',
            command=self.save
        ).pack(fill='x', pady=3)

        ttk.Button(
            save_frame,
            text='저장 후 다음',
            command=self.save_and_next
        ).pack(fill='x', pady=3)

        self.status = tk.StringVar(
            value='이미지를 선택하세요.'
        )

        tk.Label(
            save_frame,
            textvariable=self.status,
            bg='#111827',
            fg='#8792A6',
            font=('Segoe UI', 8),
            wraplength=270,
            justify='left'
        ).pack(anchor='w', pady=(5, 0))

    # ========================================================
    # 단축키
    # ========================================================

    def bind_keys(self):
        self.root.bind(
            '<Control-o>',
            lambda e: self.open_image()
        )

        self.root.bind(
            '<Control-s>',
            lambda e: self.save()
        )

        self.root.bind(
            '<Left>',
            lambda e: self.previous_image()
        )

        self.root.bind(
            '<Right>',
            lambda e: self.next_image()
        )

        self.root.bind(
            '<Delete>',
            lambda e: self.delete_selected()
        )

    # ========================================================
    # 핵심: 이미지 하나 선택
    # ========================================================

    def open_image(self):

        file_path = filedialog.askopenfilename(
            parent=self.root,
            title='이미지 파일 선택',
            filetypes=[
                (
                    '이미지 파일',
                    '*.jpg *.jpeg *.png *.bmp *.webp'
                ),
                ('JPG', '*.jpg *.jpeg'),
                ('PNG', '*.png'),
                ('BMP', '*.bmp'),
                ('WEBP', '*.webp'),
                ('모든 파일', '*.*')
            ]
        )

        if not file_path:
            return

        selected = Path(file_path)

        # 선택한 이미지 하나를 먼저 열기
        self.load_image_files(selected)

    def load_image_files(self, selected):

        folder = selected.parent

        # 선택한 이미지와 같은 폴더의 이미지 검색
        self.images = sorted(
            [
                p for p in folder.iterdir()
                if p.is_file()
                and p.suffix.lower() in IMAGE_EXTENSIONS
            ],
            key=lambda p: p.name.lower()
        )

        if not self.images:
            messagebox.showerror(
                '이미지 오류',
                '선택한 이미지 파일을 불러오지 못했습니다.'
            )
            return

        self.current_index = self.images.index(selected)

        # 이미지 목록 표시
        self.image_list.delete(0, tk.END)

        for image in self.images:
            self.image_list.insert(
                tk.END,
                image.name
            )

        self.open_current()

    # ========================================================
    # 현재 이미지 열기
    # ========================================================

    def open_current(self):

        if not self.images:
            return

        path = self.images[self.current_index]

        # 저장 안 된 변경사항 확인
        if self.dirty:

            answer = messagebox.askyesnocancel(
                '저장되지 않은 변경',
                '현재 이미지에 저장하지 않은 변경사항이 있습니다.\n'
                '저장하고 이동할까요?'
            )

            if answer is None:
                return

            if answer:
                self.save()

        try:
            self.original_image = Image.open(path).convert('RGB')

        except Exception as e:
            messagebox.showerror(
                '이미지 오류',
                f'이미지를 열 수 없습니다.\n\n{e}'
            )
            return

        self.current_image = path

        self.file_name.set(path.name)

        self.progress.set(
            f'{self.current_index + 1} / {len(self.images)}'
        )

        # 해당 이미지의 TXT 찾기
        self.load_current_labels()

        self.selected_label = None
        self.dirty = False

        # 목록 선택
        self.image_list.selection_clear(0, tk.END)
        self.image_list.selection_set(self.current_index)
        self.image_list.see(self.current_index)

        self.fit_image()
        self.refresh_objects()

        self.status.set('이미지 불러오기 완료')

    # ========================================================
    # TXT 찾기
    # ========================================================

    def get_label_path(self):

        if self.current_image is None:
            return None

        image_path = self.current_image

        # WORK가 있으면 WORK TXT 우선
        work_folder = image_path.parent / 'WORK'
        work_txt = work_folder / f'{image_path.stem}.txt'

        raw_txt = image_path.with_suffix('.txt')

        if work_txt.exists():
            return work_txt

        return raw_txt

    def load_current_labels(self):

        txt_path = self.get_label_path()

        if txt_path is None:
            self.labels = []
            return

        self.labels = load_labels(txt_path)

    # ========================================================
    # 이미지 렌더링
    # ========================================================

    def fit_image(self):

        if self.original_image is None:
            return

        self.root.update_idletasks()

        canvas_w = max(
            self.canvas.winfo_width(),
            100
        )

        canvas_h = max(
            self.canvas.winfo_height(),
            100
        )

        image_w, image_h = self.original_image.size

        self.fit_scale = min(
            canvas_w / image_w,
            canvas_h / image_h
        )

        self.scale = self.fit_scale

        self.offset_x = 0
        self.offset_y = 0

        self.render()

    def render(self):

        if self.original_image is None:
            return

        self.canvas.delete('all')

        image_w, image_h = self.original_image.size

        display_w = max(
            1,
            int(image_w * self.scale)
        )

        display_h = max(
            1,
            int(image_h * self.scale)
        )

        resized = self.original_image.resize(
            (display_w, display_h),
            Image.Resampling.LANCZOS
        )

        self.tk_image = ImageTk.PhotoImage(resized)

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        center_x = (
            canvas_w / 2 +
            self.offset_x
        )

        center_y = (
            canvas_h / 2 +
            self.offset_y
        )

        self.canvas.create_image(
            center_x,
            center_y,
            image=self.tk_image,
            anchor='center'
        )

        left = center_x - display_w / 2
        top = center_y - display_h / 2

        # BBox
        for index, label in enumerate(self.labels):

            cx = label['cx'] * image_w
            cy = label['cy'] * image_h

            bw = label['w'] * image_w
            bh = label['h'] * image_h

            x1 = left + (
                cx - bw / 2
            ) * self.scale

            y1 = top + (
                cy - bh / 2
            ) * self.scale

            x2 = left + (
                cx + bw / 2
            ) * self.scale

            y2 = top + (
                cy + bh / 2
            ) * self.scale

            class_id = label['class_id']

            color = CLASS_COLORS.get(
                class_id,
                '#FFFFFF'
            )

            width = (
                3
                if index == self.selected_label
                else 2
            )

            self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=color,
                width=width
            )

            self.canvas.create_text(
                x1 + 5,
                y1 + 4,
                text=(
                    f'{class_id} '
                    f'{CLASS_NAMES.get(class_id, "Unknown")}'
                ),
                fill=color,
                anchor='nw',
                font=('Segoe UI Semibold', 9)
            )

    # ========================================================
    # Zoom
    # ========================================================

    def zoom(self, factor):

        if self.original_image is None:
            return

        self.scale *= factor

        minimum = self.fit_scale * 0.2
        maximum = self.fit_scale * 8

        self.scale = max(
            minimum,
            min(self.scale, maximum)
        )

        self.render()

    # ========================================================
    # Pan
    # ========================================================

    def pan_down(self, event):
        self.pan_start = (
            event.x,
            event.y
        )

    def pan_drag(self, event):

        if self.pan_start is None:
            return

        dx = event.x - self.pan_start[0]
        dy = event.y - self.pan_start[1]

        self.offset_x += dx
        self.offset_y += dy

        self.pan_start = (
            event.x,
            event.y
        )

        self.render()

    def pan_up(self, event):
        self.pan_start = None

    # ========================================================
    # BBox 클릭 / 추가
    # ========================================================

    def mouse_down(self, event):

        selected = self.find_bbox(
            event.x,
            event.y
        )

        if selected is not None:

            self.selected_label = selected

            self.refresh_objects()
            self.render()

            return

        self.draw_start = (
            event.x,
            event.y
        )

    def mouse_drag(self, event):

        if self.draw_start is None:
            return

        if self.temp_box is not None:
            self.canvas.delete(
                self.temp_box
            )

        x1, y1 = self.draw_start

        self.temp_box = self.canvas.create_rectangle(
            x1,
            y1,
            event.x,
            event.y,
            outline='white',
            width=2,
            dash=(5, 3)
        )

    def mouse_up(self, event):

        if self.draw_start is None:
            return

        x1, y1 = self.draw_start
        x2, y2 = event.x, event.y

        self.draw_start = None

        if self.temp_box is not None:
            self.canvas.delete(
                self.temp_box
            )
            self.temp_box = None

        if abs(x2 - x1) < 5:
            return

        if abs(y2 - y1) < 5:
            return

        bbox = self.canvas_to_yolo(
            x1,
            y1,
            x2,
            y2
        )

        if bbox is None:
            return

        self.labels.append({
            'class_id': 0,
            **bbox
        })

        self.selected_label = (
            len(self.labels) - 1
        )

        self.dirty = True

        self.refresh_objects()
        self.render()

    def find_bbox(self, mouse_x, mouse_y):

        if self.original_image is None:
            return None

        image_w, image_h = (
            self.original_image.size
        )

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        display_w = image_w * self.scale
        display_h = image_h * self.scale

        center_x = (
            canvas_w / 2 +
            self.offset_x
        )

        center_y = (
            canvas_h / 2 +
            self.offset_y
        )

        left = center_x - display_w / 2
        top = center_y - display_h / 2

        for index in range(
            len(self.labels) - 1,
            -1,
            -1
        ):

            label = self.labels[index]

            cx = label['cx'] * image_w
            cy = label['cy'] * image_h
            bw = label['w'] * image_w
            bh = label['h'] * image_h

            x1 = left + (
                cx - bw / 2
            ) * self.scale

            y1 = top + (
                cy - bh / 2
            ) * self.scale

            x2 = left + (
                cx + bw / 2
            ) * self.scale

            y2 = top + (
                cy + bh / 2
            ) * self.scale

            if (
                x1 <= mouse_x <= x2
                and
                y1 <= mouse_y <= y2
            ):
                return index

        return None

    def canvas_to_yolo(
        self,
        x1,
        y1,
        x2,
        y2
    ):

        if self.original_image is None:
            return None

        image_w, image_h = (
            self.original_image.size
        )

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        display_w = image_w * self.scale
        display_h = image_h * self.scale

        center_x = (
            canvas_w / 2 +
            self.offset_x
        )

        center_y = (
            canvas_h / 2 +
            self.offset_y
        )

        left = center_x - display_w / 2
        top = center_y - display_h / 2

        ix1 = (
            x1 - left
        ) / self.scale

        iy1 = (
            y1 - top
        ) / self.scale

        ix2 = (
            x2 - left
        ) / self.scale

        iy2 = (
            y2 - top
        ) / self.scale

        ix1 = max(
            0,
            min(image_w, ix1)
        )

        iy1 = max(
            0,
            min(image_h, iy1)
        )

        ix2 = max(
            0,
            min(image_w, ix2)
        )

        iy2 = max(
            0,
            min(image_h, iy2)
        )

        if ix2 <= ix1 or iy2 <= iy1:
            return None

        return {
            'cx': ((ix1 + ix2) / 2) / image_w,
            'cy': ((iy1 + iy2) / 2) / image_h,
            'w': (ix2 - ix1) / image_w,
            'h': (iy2 - iy1) / image_h
        }

    # ========================================================
    # Object
    # ========================================================

    def refresh_objects(self):

        self.object_list.delete(
            0,
            tk.END
        )

        for i, label in enumerate(
            self.labels
        ):

            class_id = label['class_id']

            self.object_list.insert(
                tk.END,
                (
                    f'#{i + 1}   '
                    f'Class {class_id} · '
                    f'{CLASS_NAMES.get(class_id, "Unknown")}'
                )
            )

        if (
            self.selected_label is not None
            and
            self.selected_label < len(self.labels)
        ):

            self.object_list.selection_set(
                self.selected_label
            )

            class_id = self.labels[
                self.selected_label
            ]['class_id']

            self.class_var.set(
                f'{class_id} · {CLASS_NAMES[class_id]}'
            )

    def object_selected(self, event=None):

        selection = (
            self.object_list.curselection()
        )

        if not selection:
            return

        self.selected_label = selection[0]

        class_id = self.labels[
            self.selected_label
        ]['class_id']

        self.class_var.set(
            f'{class_id} · {CLASS_NAMES[class_id]}'
        )

        self.render()

    def change_class(self, event=None):

        if self.selected_label is None:
            return

        value = self.class_var.get()

        if not value:
            return

        class_id = int(
            value.split('·')[0].strip()
        )

        self.labels[
            self.selected_label
        ]['class_id'] = class_id

        self.dirty = True

        self.refresh_objects()
        self.render()

    def add_bbox_message(self):
        self.status.set(
            '이미지에서 마우스로 드래그하면 BBox가 추가됩니다.'
        )

    def delete_selected(self):

        if self.selected_label is None:
            return

        if not self.labels:
            return

        del self.labels[
            self.selected_label
        ]

        self.selected_label = None
        self.dirty = True

        self.refresh_objects()
        self.render()

    # ========================================================
    # 저장
    # ========================================================

    def save(self):

        if self.current_image is None:
            return

        work_folder = (
            self.current_image.parent / 'WORK'
        )

        work_folder.mkdir(
            exist_ok=True
        )

        txt_path = (
            work_folder /
            f'{self.current_image.stem}.txt'
        )

        try:
            save_labels(
                txt_path,
                self.labels
            )

            self.save_csv()

            self.dirty = False

            self.status.set(
                f'저장 완료 · WORK/{txt_path.name}'
            )

        except Exception as e:
            messagebox.showerror(
                '저장 오류',
                str(e)
            )

    def save_csv(self):

        if self.current_image is None:
            return

        work_folder = (
            self.current_image.parent / 'WORK'
        )

        csv_path = (
            work_folder /
            'manifest.csv'
        )

        rows = []

        for image in self.images:

            txt = (
                work_folder /
                f'{image.stem}.txt'
            )

            rows.append({
                'filename': image.name,
                'label_file': (
                    txt.name
                    if txt.exists()
                    else ''
                ),
                'status': (
                    'EDITED'
                    if txt.exists()
                    else 'REVIEW'
                )
            })

        with open(
            csv_path,
            'w',
            newline='',
            encoding='utf-8-sig'
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=[
                    'filename',
                    'label_file',
                    'status'
                ]
            )

            writer.writeheader()
            writer.writerows(rows)

    def save_and_next(self):

        self.save()

        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.open_current()

    # ========================================================
    # 이동
    # ========================================================

    def check_unsaved(self):

        if not self.dirty:
            return True

        answer = messagebox.askyesnocancel(
            '저장되지 않은 변경',
            '수정한 내용이 저장되지 않았습니다.\n'
            '저장하고 이동할까요?'
        )

        if answer is None:
            return False

        if answer:
            self.save()

        return True

    def previous_image(self):

        if self.current_index <= 0:
            return

        if not self.check_unsaved():
            return

        self.current_index -= 1
        self.open_current()

    def next_image(self):

        if (
            self.current_index < 0
            or
            self.current_index >= len(self.images) - 1
        ):
            return

        if not self.check_unsaved():
            return

        self.current_index += 1
        self.open_current()

    def list_selected(self, event=None):

        selection = (
            self.image_list.curselection()
        )

        if not selection:
            return

        new_index = selection[0]

        if new_index == self.current_index:
            return

        if not self.check_unsaved():
            return

        self.current_index = new_index
        self.open_current()


# ============================================================
# 실행
# ============================================================

if __name__ == '__main__':
    root = tk.Tk()
    app = LabelingApp(root)
    root.mainloop()
