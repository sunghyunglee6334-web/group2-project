import tkinter as tk
from tkinter import ttk


def show_result():
    """
    Entry와 Combobox에서 현재 값을 읽어서
    result_label에 표시합니다.
    """

    file_name = file_name_var.get()
    class_name = class_var.get()

    if file_name == "":
        result_label.config(
            text="파일명을 입력하세요."
        )
        return

    if class_name == "":
        result_label.config(
            text="Class를 선택하세요."
        )
        return

    result_text = (
        f"파일명: {file_name}\n"
        f"선택 Class: {class_name}"
    )

    result_label.config(text=result_text)


# --------------------------------------------------
# 1. Window 생성
# --------------------------------------------------

root = tk.Tk()
root.title("예제 2 - 라벨 정보 입력")
root.geometry("550x350")


# --------------------------------------------------
# 2. GUI에서 사용할 변수
# --------------------------------------------------

file_name_var = tk.StringVar()
class_var = tk.StringVar()


# --------------------------------------------------
# 3. 제목
# --------------------------------------------------

title_label = tk.Label(
    root,
    text="라벨링 정보 입력 연습",
    font=("Arial", 18)
)

title_label.grid(
    row=0,
    column=0,
    columnspan=2,
    pady=25
)


# --------------------------------------------------
# 4. 파일명 입력
# --------------------------------------------------

file_label = tk.Label(
    root,
    text="이미지 파일명:"
)

file_label.grid(
    row=1,
    column=0,
    padx=20,
    pady=10,
    sticky="e"
)


file_entry = tk.Entry(
    root,
    textvariable=file_name_var,
    width=30
)

file_entry.grid(
    row=1,
    column=1,
    padx=20,
    pady=10
)


# --------------------------------------------------
# 5. Class 선택
# --------------------------------------------------

class_label = tk.Label(
    root,
    text="Class:"
)

class_label.grid(
    row=2,
    column=0,
    padx=20,
    pady=10,
    sticky="e"
)


class_combo = ttk.Combobox(
    root,
    textvariable=class_var,
    values=[
        "leaf",
        "plastic",
        "metal",
        "disease"
    ],
    state="readonly",
    width=27
)

class_combo.grid(
    row=2,
    column=1,
    padx=20,
    pady=10
)


# --------------------------------------------------
# 6. 확인 버튼
# --------------------------------------------------

save_button = tk.Button(
    root,
    text="입력 확인",
    command=show_result,
    width=20,
    height=2
)

save_button.grid(
    row=3,
    column=0,
    columnspan=2,
    pady=20
)


# --------------------------------------------------
# 7. 결과 표시 Label
# --------------------------------------------------

result_label = tk.Label(
    root,
    text="파일명과 Class를 입력해 주세요.",
    font=("Arial", 11)
)

result_label.grid(
    row=4,
    column=0,
    columnspan=2,
    pady=10
)


# --------------------------------------------------
# 8. GUI 실행
# --------------------------------------------------

root.mainloop()