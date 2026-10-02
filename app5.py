import tkinter as tk


# -------------------------
# 변수
# -------------------------

start_x = 0
start_y = 0

current_rect = None


# -------------------------
# 함수
# -------------------------

def on_mouse_down(event):

    global start_x, start_y, current_rect

    start_x = event.x
    start_y = event.y

    current_rect = canvas.create_rectangle(
        start_x,
        start_y,
        start_x,
        start_y,
        outline="red",
        width=2
    )


def on_mouse_drag(event):

    if current_rect is None:
        return

    canvas.coords(
        current_rect,
        start_x,
        start_y,
        event.x,
        event.y
    )


def on_mouse_up(event):

    end_x = event.x
    end_y = event.y

    status_label.config(
        text=f"BBox: ({start_x}, {start_y}) ~ ({end_x}, {end_y})"
    )


def clear_bbox():

    global current_rect

    canvas.delete("all")

    current_rect = None

    status_label.config(
        text="BBox를 다시 그려보세요."
    )


# -------------------------
# 화면 만들기
# -------------------------

root = tk.Tk()

root.title("BBox 라벨링 연습")
root.geometry("800x650")


title_label = tk.Label(
    root,
    text="마우스로 BBox를 그려보세요."
)

title_label.pack()


canvas = tk.Canvas(
    root,
    width=700,
    height=450,
    bg="white"
)

canvas.pack()


clear_button = tk.Button(
    root,
    text="BBox 삭제",
    command=clear_bbox
)

clear_button.pack()


status_label = tk.Label(
    root,
    text="아직 BBox가 없습니다."
)

status_label.pack()


# -------------------------
# 마우스 이벤트 연결
# -------------------------

canvas.bind("<Button-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_drag)
canvas.bind("<ButtonRelease-1>", on_mouse_up)


# -------------------------
# 프로그램 실행
# -------------------------

root.mainloop()