#!/usr/bin/env python3
"""
Simple examples of Windows-style path input dialogs using tkinter.
Run with: python .\path_dialog_examples.py
"""

import tkinter as tk
from tkinter import filedialog, simpledialog


def choose_file():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select a file",
        initialdir="C:\\",
        filetypes=[("All files", "*.*")],
    )
    return path


def choose_files():
    root = tk.Tk()
    root.withdraw()
    paths = filedialog.askopenfilenames(
        title="Select one or more files",
        initialdir="C:\\",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    return list(paths)


def choose_directory():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askdirectory(
        title="Select a folder",
        initialdir="C:\\",
    )
    return path


def save_file():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.asksaveasfilename(
        title="Save file as",
        initialdir="C:\\",
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    return path


def ask_text_input(prompt="Enter path or text:"):
    root = tk.Tk()
    root.withdraw()
    ans = simpledialog.askstring("Input", prompt)
    return ans


def main():
    print("Choose an action:")
    print(
        "1) Open file  2) Open files  3) Choose folder  4) Save file  5) Enter path string"
    )
    choice = input("Enter 1-5: ").strip()
    if choice == "1":
        print("Selected:", choose_file())
    elif choice == "2":
        print("Selected:", choose_files())
    elif choice == "3":
        print("Selected:", choose_directory())
    elif choice == "4":
        print("Selected:", save_file())
    elif choice == "5":
        print("Entered:", ask_text_input())
    else:
        print("No action selected. Exiting.")


if __name__ == "__main__":
    main()
