import tkinter as tk
from Class_SignUp_and_Login import SignUp

class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self._frame = None
        self.switch_frames(SignUp)
        self.details()

    def switch_frames(self, frame_class):
        new_frame = frame_class(self)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack()

    def details(self):
        self.geometry("720x580")
        self.title("Sign Up / Log In")


if __name__ == "__main__":
    app = App()
    app.mainloop()
