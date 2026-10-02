import tkinter as tk

def on_mouse_down(event):

    print(event.x) 
    print(event.y)

root = tk.Tk()
root.title("Undo 연습")
root.geometry("800x650")

canvas = tk.Canvas(
    root,
    width=700,
    height=450,
    bg="white"
) 

canvas.pack()

canvas.bind("<Button-1>", on_mouse_down)

root.mainloop()