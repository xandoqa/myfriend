from tkinter import *

class Aplication:
    def __init__(self, master=None):
        self.canvas = Canvas(master, width=1366, height=768, bg="#b3d9ff")
        self.canvas.pack()

        centro_x = 1366 // 2
        centro_y = 768 // 2
        raio = 50

        self.canvas.create_oval(
            centro_x - raio,
            centro_y - raio,
            centro_x + raio,
            centro_y + raio,
            fill="blue"
        )

root = Tk()
root.title("MyFriend: The Psychologist Machine")
root.geometry("1366x768")
root.configure(bg="#b3d9ff")

Aplication(root)

root.mainloop()