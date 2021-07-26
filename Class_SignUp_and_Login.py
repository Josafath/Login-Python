import tkinter as tk
from tkinter.font import Font
from tkinter import messagebox as mb
import datetime

class SignUp(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.user_name = tk.StringVar()
        self.email = tk.StringVar()
        self.password = tk.StringVar()
        self.myfont = Font(family="Times New Roman", size=18)
        self.myfont_entry = Font(family="Helvetica", size=18)
        #Elements in the frame
        tk.Label(self, text="User Name:",font = self.myfont).pack(pady=10)
        tk.Entry(self,justify = "center",font = self.myfont_entry,textvariable =self.user_name,bg = "white").pack(pady=10)
        tk.Label(self,text="Email:", font=self.myfont).pack(pady=10)
        tk.Entry(self, justify= "center", font= self.myfont_entry, textvariable = self.email, bg="white").pack(pady=10)
        tk.Label(self, text="Password:", font=self.myfont).pack(pady=10)
        tk.Entry(self, justify="center",show="*", font=self.myfont_entry, textvariable=self.password, bg="white").pack(pady=10)
        tk.Button(self,text = "Sign Up",font = self.myfont, relief = "raised",command = self.registrar,background = "#07bedb",fg="#e3e3e3").pack(pady=40)

        tk.Label(self,text="Do you already have an account with us? Then log in. :)").pack(padx=10)
        tk.Button(self,text="Log In",relief="groove",command=lambda: master.switch_frames(LogIn)).pack()

    def registrar(self):
        # Check the input Data
        right_input = self.check_email_and_password()
        if not right_input:
            mb.showerror("You made something bad","Try to put all the data required, please. \nPassword must be at least 8 characters length.\nEmail must have the simbol @")

        else:
            sign_up_file = open("Users.txt", "a")
            fecha = datetime.now()
            date_format = fecha.strftime(" %d/%B/%Y-(%H:%M:%S) ")
            user = "\n" + self.user_name.get().lower() + " " + self.email.get()+ " " + self.password.get().lower() + " " + date_format
            sign_up_file.write(user)
            sign_up_file.close()
            extract_data = open("Users.txt","r")

            # Let's split every single line to be able to sort the data
            # We gonna have something like: [[user_name, email, password],[user_name, email, password]...]

            users = [line.split() for line in extract_data]
            if not len(users) < 2:
                self.sort(users)
                users_sorted = open("Users.txt", 'w')
                for persona in users:
                    person = ' '.join([str(elem) for elem in persona])  # I made this loop to get the user data without the "[]".
                    users_sorted.write(person + "\n")

                self.clean_entries()
                mb.showinfo("","Now you can login in this program.:)")

    def sort(self, array):

        if len(array) > 1:
            mid = len(array) // 2
            L = array[:mid]
            R = array[mid:]

            self.sort(L)
            self.sort(R)

            i = j = k = 0

            while i < len(L) and j < len(R):
                if ord(L[i][0][0]) < ord(R[j][0][0]):
                    array[k] = L[i]
                    i += 1

                else:
                    array[k] = R[j]
                    j += 1
                k += 1

            while i < len(L):
                array[k] = L[i]
                i += 1
                j += 1

            while j < len(R):
                array[k] = R[j]
                j += 1
                k += 1

            return array



    def check_email_and_password(self):
        is_ok = True
        # Statement for password input
        if len(self.password.get()) < 8:
            is_ok = False

        # Statement for email input
        elif self.email.get().find('@') == -1 or len(self.email.get()) == 0 or self.email.get().islower() is False:
            is_ok = False

        return is_ok

    def clean_entries(self):
        self.email.set("")
        self.user_name.set("")
        self.password.set("")



class LogIn(tk.Frame):
    def __init__(self,master):
        tk.Frame.__init__(self,master)
        self.user_name = tk.StringVar()
        self.password = tk.StringVar()
        self.fecha = tk.StringVar()
        self.info = tk.StringVar()
        self.user = tk.StringVar()
        self.myfont = Font(family="Times New Roman", size=18)
        self.myfont_entry = Font(family="Helvetica", size=18)
        tk.Label(self, text="User Name:", font=self.myfont).pack(pady=10)
        tk.Entry(self, justify="center", font=self.myfont_entry, textvariable=self.user_name, bg="white").pack(pady=10)
        tk.Label(self, text="Password:", font=self.myfont).pack(pady=10)
        tk.Entry(self, justify="center", show="*", font=self.myfont_entry, textvariable=self.password, bg="white").pack(pady=10)
        tk.Button(self, text="Log In", font=self.myfont, relief="raised",command=self.login,background = "#07bedb",fg="#e3e3e3").pack(pady=40)

        tk.Button(self, text="<-- Back", relief="groove",font=Font(size=12), background = "#fc92e2", fg="#e3e3e3", command=lambda: master.switch_frames(SignUp)).pack()
        tk.Label(self, textvariable=self.user,font= self.myfont).pack(pady=15)

        tk.Label(self, textvariable=self.info, font=self.myfont, background="#b8f2e6").pack(pady=25, padx=20, side="left")
        tk.Label(self, textvariable=self.fecha, font=self.myfont, background="#b8f2e6").pack(pady=30, padx=5, side="right")

    def login(self):
        sign_in = open("Users.txt", 'r')
        users = [line.split() for line in sign_in]
        self.search_user(users,len(users)-1,0,self.user_name.get().lower(), self.password.get().lower())
        self.clean_entries()

    def search_user(self, array, high, low, target, password):
        try:
            if high >= low:
                mid = (high + low) // 2
                # In case the program found the user then first set the user info and after update the date of the last login.

                if ord(array[mid][0][0]) == ord(target[0]) and array[mid][2] == password:
                    self.user.set(f"Welcome back {array[mid][0].capitalize()}!")
                    self.info.set(f"Email: {array[mid][1]}")
                    self.fecha.set("Register Date:" + "\n" + f"{array[mid][-1]}")
                    return

                elif ord(array[mid][0][0]) > ord(target[0]):
                    return self.search_user(array, low, mid - 1, target, password)

                elif ord(array[mid][0][0]) < ord(target[0]):
                    return self.search_user(array, mid + 1, high, target, password)

                else:
                    return 0

        # In case the user insert a name out of the range of the current list of users.
        except IndexError:
            self.user.set("User NOT Found")

    def clean_entries(self):
        self.user_name.set("")
        self.password.set("")

