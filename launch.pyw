"""Double-click this file to open the Support at Home statements window (runs with pythonw: no console).
It checks ReportLab and Pillow are installed first. It never installs anything itself."""
import os, sys, traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))   # program files


def alert(title, text):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror(title, text, parent=root)
        root.destroy()
    except Exception:   # Tk itself unavailable: fall back to a plain Windows message box
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)


missing = []
for module, package in (("reportlab", "reportlab"), ("PIL", "pillow")):
    try:
        __import__(module)
    except ImportError:
        missing.append(package)
if missing:
    name = "ReportLab" if "reportlab" in missing else "Pillow"
    alert("Support at Home statements",
          f"{name} is not installed. Open Command Prompt and run:\n\n    py -m pip install {' '.join(missing)}\n\n"
          "Then double-click launch.pyw again.")
    sys.exit(1)

try:
    import sah_gui
except Exception:
    alert("Support at Home statements", "The app couldn't start:\n\n" + traceback.format_exc(limit=3))
    sys.exit(1)
sah_gui.main()
