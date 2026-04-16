import tkinter as tk

class App(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()

# cria a janela principal
root = tk.Tk()

# define tamanho fixo 720x360
root.geometry("720x360")

# cria a aplicação dentro da janela
myapp = App(master=root)

# configurações da janela
root.title("MyFriend v1.0")
root.maxsize(720, 360)

# inicia o loop
myapp.mainloop()
