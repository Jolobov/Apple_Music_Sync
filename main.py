# main.py
import tkinter as tk
from tkinter import ttk
from gui import GamdlGUI

if __name__ == "__main__":
    root = tk.Tk()

    try:
        style = ttk.Style()
        style.theme_use('clam')
    except tk.TclError:
        pass

    app = GamdlGUI(root)
    root.mainloop()