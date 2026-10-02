import tkinter as tk

def change_message():
  """
  버튼을 눌렀을 때 실행되는 함수입니다
  message_lable의 글자를 새로운 문자으로 바꿉니다.
  """
  message_label.config(text="버튼을 눌렀습니다")

#1. 프로그램의 기본 window를 만듭니다.
root = tk.Tk()

#2. Window 제목을 설정합니다.
root.title("예제 1 - Tkinter 기본 화면")


#3. window 크기를 설정합니다.
root.geometry("500x300")

#4. 제목을 표시하는 Lable을 만듭니다.
title_label = tk.Label(
  root,
  text="교과 7 Tkinter 첫 번째 실습",
  font=("Arial", 18)
)
title_label.pack(pady=10)

#5. 상태 메세지를 표시하는 Label을 만듭니다.
message_label = tk.Label(
  root,
  text="아래 버튼을 눌러보세요.",
  font=("Arial", 12)
)
message_label.pack(pady=10)

#6. Button을 만듭니다.
change_button = tk.Button(
  root,
  text="메세지 변경",
  command=change_message,
  width=15,
  height=2
)
change_button.pack(pady=20)

# 7. GUI 프로그램을 계속 실행합니다.
root.mainloop()




