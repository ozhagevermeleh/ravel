import tkinter as tk
import socket
import sys
from tkinter.simpledialog import askstring
from tkinter import *
from tkinter import messagebox
import time
import threading
import protocol
from queue import Queue
import miniaudio


IP = "127.0.0.1"
PORT = 1234
BIG_BUFFER = 256
stop_event = threading.Event()


logged_in = False
app_lock = threading.Lock()


def packed(cmd):
    return cmd.encode()


class SharedApp:
    def __init__(self, app):  # for sharing the app, helpful when it changes from log-in window to main app
        self.app = app

    def set_app(self, app):
        self.app = app

    def get_app(self):
        return self.app


def receive_data_from_server(client, shared_app):
    while not stop_event.isSet():
        try:
            server_cmd = client.recv(BIG_BUFFER).decode()
            if server_cmd:
                print(server_cmd)
                if protocol.check_cmd(server_cmd):
                    app = shared_app.get_app()
                    if app:
                        app.handle_server_response(server_cmd)
                else:
                    print("invalid cmd: " + server_cmd)
        except Exception as err:
            print(err)


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)  # scrollable frame, interface helpful for the main window

        canvas = tk.Canvas(self)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y", expand=False)
        canvas.pack(side="left", fill="both", expand=True)

        self.canvas = canvas
        self.scrollable_frame = scrollable_frame


class LogInWindow(tk.Tk):
    def __init__(self, client, shared_app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shared_app = shared_app
        self.lock = threading.Lock()
        self.client = client

        self.title("Log In")
        self.geometry("500x400")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)  # Proper handling of window close

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        self.frames = {}
        for F in (LoginPage, RegisterPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=1, sticky="nsew")

        self.show_frame(LoginPage)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()

    def login_successful(self):
        global logged_in  # the user is logged in now
        logged_in = True
        self.destroy()  # destroy the current main application

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to close the application?"):
            self.client.send(packed("exit"))
            stop_event.set()
            self.destroy()

    def send(self, msg):
        self.client.send(packed(msg))

    def handle_server_response(self, response):
        if response == "log_in_acc":
            self.login_successful()
        elif response == "log_in_err":
            self.frames[LoginPage].error_label.config(text="Invalid username or password")
        elif response == "registered":
            self.frames[RegisterPage].error_label.config(text="Registered!", fg="green")
        elif response == "error_registering_pass":
            self.frames[RegisterPage].error_label.config(text="Not registered, passwords do not match!", fg="red")
        elif response == "error_registering_name":
            self.frames[RegisterPage].error_label.config(text="Not registered, name already exists!", fg="red")
        else:
            print("Unknown response from server:", response)


class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        label = tk.Label(self, text="Login Page", font=("Helvetica", 18))
        label.pack(pady=10, padx=10)

        username_label = tk.Label(self, text="Username:")
        username_label.pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()

        password_label = tk.Label(self, text="Password:")
        password_label.pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()

        login_button = tk.Button(self, text="Login", command=self.login)
        login_button.pack(pady=5)

        register_button = tk.Button(self, text="Register", command=lambda: controller.show_frame(RegisterPage))
        register_button.pack(pady=5)

        self.error_label = tk.Label(self, text="", fg="red")
        self.error_label.pack(pady=5)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        self.controller.send("log_in-" + username + "-" + password)


class RegisterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        label = tk.Label(self, text="Register Page", font=("Helvetica", 18))
        label.pack(pady=10, padx=10)

        username_label = tk.Label(self, text="Choose Username:")
        username_label.pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()

        password_label = tk.Label(self, text="Choose Password:")
        password_label.pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()

        password2_label = tk.Label(self, text="Type Password again:")
        password2_label.pack()
        self.password2_entry = tk.Entry(self, show="*")
        self.password2_entry.pack()

        register_button = tk.Button(self, text="Register", command=self.register)
        register_button.pack(pady=5)

        back_button = tk.Button(self, text="Back to Login", command=lambda: controller.show_frame(LoginPage))
        back_button.pack(pady=5)

        self.error_label = tk.Label(self, text="", fg="red")
        self.error_label.pack(pady=5)

    def register(self):  # todo send log in request and receive, add error

        username = self.username_entry.get()
        password = self.password_entry.get()
        password2 = self.password2_entry.get()

        self.controller.send("register-" + username + "-" + password + "-" + password2)


class MainApplication(tk.Tk):
    def __init__(self, client, shared_app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shared_app = shared_app
        self.client = client

        self.title("Ravel")
        self.geometry("1920x1080")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)  # proper handling of window close

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        self.frames = {}
        for F in (StartPage, PageOne, PageTwo):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=1, sticky="nsew")

        self.help_screen = LibraryScreen(container)
        self.help_screen.grid(row=0, column=0, sticky="ns")

        self.player_screen = PlayerScreen(self)
        self.player_screen.pack(side="bottom", fill="x")

        self.show_frame(StartPage)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to close the application?"):
            self.client.send(packed("exit"))
            stop_event.set()
            self.destroy()  # ensuring proper closure of the application


    def send(self, msg):
        self.client.send(packed(msg))

    def handle_server_response(self, response):
        if response == "log_in_err":
            print("h")
        elif response == " ":
            print("g1")
        else:
            print("Unknown response from server:", response)


class StartPage(ScrollableFrame):
    def __init__(self, parent, controller):  # todo add search for music and option to play
        super().__init__(parent)

        label = tk.Label(self.scrollable_frame, text="Start Page", font=("Helvetica", 18))
        label.pack(pady=10, padx=10)

        # Add some sample text to make it long enough to scroll
        for i in range(50):
            tk.Label(self.scrollable_frame, text=f"Label {i}").pack()

        button1 = tk.Button(self.scrollable_frame, text="Go to Page One",
                            command=lambda: controller.send("log_in-b-c"))
        button1.pack()

        button2 = tk.Button(self.scrollable_frame, text="Go to Page Two",
                            command=lambda: controller.show_frame(PageTwo))
        button2.pack()


class PageOne(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        label = tk.Label(self, text="Page One", font=("Helvetica", 18))
        label.pack(pady=10, padx=10)

        button = tk.Button(self, text="Go to Start Page",
                           command=lambda: controller.show_frame(StartPage))
        button.pack()


class PageTwo(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        label = tk.Label(self, text="Page Two", font=("Helvetica", 18))
        label.pack(pady=10, padx=10)

        button = tk.Button(self, text="Go to Start Page",
                           command=lambda: controller.show_frame(StartPage))
        button.pack()


class LibraryScreen(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        label = tk.Label(self, text="Library Screen", font=("Helvetica", 14))
        label.pack(side="left", padx=10, pady=10)


class PlayerScreen(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg="lightgray", height=100)
        label = tk.Label(self, text="Player Screen", font=("Helvetica", 14))
        label.pack(pady=10, padx=10, fill="both", expand=True)


class Player:
    def __init__(self):
        self.device = miniaudio.PlaybackDevice()
        self.playing = False
        self.stream_thread = None

    def load_and_play(self, filename):
        # stop playback if it's already playing
        if self.playing:
            self.stop()

        file_format = miniaudio.SampleFormat.FLAC  # todo: support for mp3 for local files

        # open and start playback
        self.device.start(lambda in_data, frame_count, time_info, status_flags: self.stream_callback(
            filename, in_data, frame_count), filename, file_format)
        self.playing = True

        # Start streaming thread for FLAC files
        if file_format == miniaudio.SampleFormat.FLAC:
            self.stream_thread = threading.Thread(target=self.stream_flac_file, args=(filename,))
            self.stream_thread.start()

    def stop(self):
        # stop playback
        if self.playing:
            self.device.stop()
            self.playing = False

        # stop streaming thread
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join()


def main():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((IP, PORT))  # connect to server
    except Exception as error:
        print(error)  # could be an error connecting to server or establishing the socket

    shared_app = SharedApp(None)
    app = LogInWindow(client, shared_app)
    shared_app.set_app(app)

    data_thread = threading.Thread(target=receive_data_from_server, args=(client, shared_app))
    data_thread.daemon = True
    data_thread.start()

    if not stop_event.isSet():
        app.mainloop()

    if logged_in:
        app = MainApplication(client, shared_app)
        shared_app.set_app(app)
        if not stop_event.isSet():
            app.mainloop()

    stop_event.set()
    data_thread.join()
    client.close()


if __name__ == "__main__":
    main()



