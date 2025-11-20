import tkinter as tk
from tkinter import filedialog


def choose_directory():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askdirectory(
        title="Select a folder",
        initialdir="C:\\",
    )
    return path
