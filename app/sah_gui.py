"""Support at Home statements - Windows window (Tkinter, standard library only).
Start it by double-clicking launch.pyw. Everything runs on this PC; nothing is sent anywhere.

Threading: statements are built by sah_statement.run() on a background thread. That thread only puts
messages on a queue; the window reads the queue every 100 ms with root.after(). No Tk call is ever made
from the worker, and build() is never called on the window's thread."""
import datetime as dt, json, os, queue, sys, threading, traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import sah_statement as sah

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # main folder (this file lives in app)
APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "SAHStatements")
SETTINGS = os.path.join(APP_DIR, "settings.json")
CRASH_LOG = os.path.join(APP_DIR, "crash.log")
MAX_ROWS = 2000   # results list keeps the latest rows only
RED = "#B00020"


def log_crash(text):
    """Append a traceback to crash.log. Never raises."""
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"---- {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n{text}\n")
    except OSError:
        pass


def show_crash(text):
    log_crash(text)
    messagebox.showerror("Something went wrong",
                         "Sorry, something unexpected went wrong.\n\n"
                         f"{text.strip().splitlines()[-1]}\n\nDetails were saved to:\n{CRASH_LOG}")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            s = json.load(f)
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(s):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except OSError:
        pass   # remembering paths is a convenience, not worth an error


def default_paths(saved):
    """Saved paths if still there, else the sample files and statements folder next to the app."""
    paths = {}
    for key, name in (("clients", "clients.csv"), ("items", "line_items.csv"), ("outdir", "statements")):
        p = saved.get(key) or os.path.join(ROOT, name)
        paths[key] = p if key == "outdir" or os.path.isfile(p) else ""
    return paths


def time_left(seconds):
    if seconds < 60:
        return "less than a minute left"
    m = round(seconds / 60)
    return f"about {m // 60}h {m % 60}m left" if m >= 60 else f"about {m}m left"


def open_path(path):
    try:
        os.startfile(path)
    except OSError as ex:
        messagebox.showerror("Can't open", f"Windows couldn't open:\n{path}\n\n{ex.strerror or ex}")


class App:
    def __init__(self, root):
        self.root, self.q, self.worker, self.cancel, self.closing, self.closed = root, queue.Queue(), None, None, False, False
        root.title("Support at Home statements")
        root.minsize(640, 520)
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#00539B")
        style.configure("Big.TButton", font=("Segoe UI", 11, "bold"), padding=(18, 8))

        self.paths = {k: tk.StringVar(value=v) for k, v in default_paths(load_settings()).items()}

        f = ttk.Frame(root, padding=16)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        ttk.Label(f, text="Support at Home statements", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        self.entries, self.browse_btns = [], []
        for r, (key, label, folder) in enumerate([("clients", "Clients file (CSV)", False),
                                                  ("items", "Line items file (CSV)", False),
                                                  ("outdir", "Save statements to", True)], start=1):
            ttk.Label(f, text=label).grid(row=r, column=0, sticky="w", padx=(0, 10), pady=4)
            e = ttk.Entry(f, textvariable=self.paths[key], state="readonly")
            e.grid(row=r, column=1, sticky="ew", pady=4)
            b = ttk.Button(f, text="Browse…", command=lambda k=key, d=folder: self.browse(k, d))
            b.grid(row=r, column=2, padx=(8, 0), pady=4)
            self.entries.append(e); self.browse_btns.append(b)

        self.create_btn = ttk.Button(f, text="Create statements", style="Big.TButton", command=self.start)
        self.create_btn.grid(row=4, column=0, columnspan=3, pady=(14, 10))

        self.bar = ttk.Progressbar(f, mode="determinate", maximum=1)
        self.bar.grid(row=5, column=0, columnspan=3, sticky="ew")
        self.status = tk.StringVar(value="Choose your files, then click Create statements.")
        ttk.Label(f, textvariable=self.status).grid(row=6, column=0, columnspan=3, sticky="w", pady=(6, 8))

        lf = ttk.Frame(f)
        lf.grid(row=7, column=0, columnspan=3, sticky="nsew")
        f.rowconfigure(7, weight=1)
        self.rows = tk.Listbox(lf, activestyle="none", font=("Segoe UI", 10), borderwidth=1, relief="solid", highlightthickness=0)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.rows.yview)
        self.rows.configure(yscrollcommand=sb.set)
        self.rows.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        bf = ttk.Frame(f)
        bf.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        self.cancel_btn = ttk.Button(bf, text="Cancel", command=self.request_cancel, state="disabled")
        self.cancel_btn.pack(side="left")
        self.reset_btn = ttk.Button(bf, text="Reset", command=self.reset)
        self.reset_btn.pack(side="left", padx=(8, 0))
        self.log_btn = ttk.Button(bf, text="Open error log", command=lambda: open_path(self.out_file("errors.log")))
        self.log_btn.pack(side="right")
        self.dash_btn = ttk.Button(bf, text="Open dashboard", command=lambda: open_path(self.out_file("status.html")))
        self.dash_btn.pack(side="right", padx=(0, 8))
        ttk.Button(bf, text="Open folder", command=self.open_folder).pack(side="right", padx=(0, 8))

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_buttons()
        root.after(100, self.poll)

    # ---- helpers ----
    def out_file(self, name):
        return os.path.join(self.paths["outdir"].get(), name)

    def running(self):
        return self.worker is not None and self.worker.is_alive()

    def refresh_buttons(self):
        busy = self.running()
        for e in self.entries:
            e.configure(state="disabled" if busy else "readonly")
        for w in self.browse_btns + [self.create_btn, self.reset_btn]:
            w.configure(state="disabled" if busy else "normal")
        self.cancel_btn.configure(state="normal" if busy and not self.cancel.is_set() else "disabled")
        self.dash_btn.configure(state="normal" if os.path.isfile(self.out_file("status.html")) else "disabled")
        self.log_btn.configure(state="normal" if not busy and os.path.isfile(self.out_file("errors.log")) else "disabled")

    def browse(self, key, folder):
        cur = self.paths[key].get()
        start = cur if folder else os.path.dirname(cur) if cur else ROOT
        if folder:
            p = filedialog.askdirectory(parent=self.root, title="Save statements to", initialdir=start if os.path.isdir(start) else ROOT)
        else:
            p = filedialog.askopenfilename(parent=self.root, title="Choose a CSV file", initialdir=start or ROOT,
                                           filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if p:
            self.paths[key].set(os.path.normpath(p))
            save_settings({k: v.get() for k, v in self.paths.items()})
            self.refresh_buttons()

    def reset(self):
        """Start again: clear the last run from the window and go back to the default files.
        Statements already created are left where they are."""
        if self.running():
            return
        for k, v in default_paths({}).items():
            self.paths[k].set(v)
        save_settings({k: v.get() for k, v in self.paths.items()})
        self.rows.delete(0, "end")
        self.bar.configure(value=0, maximum=1)
        self.status.set("Choose your files, then click Create statements.")
        self.refresh_buttons()

    def open_folder(self):
        d = self.paths["outdir"].get()
        if not os.path.isdir(d):
            messagebox.showinfo("Folder not created yet", f"This folder doesn't exist yet. It will be created when you create statements:\n{d}")
            return
        open_path(d)

    # ---- run ----
    def start(self):
        clients, items, outdir = (self.paths[k].get() for k in ("clients", "items", "outdir"))
        problems = sah.validate_inputs(clients, items)
        if not outdir:
            problems.append("Choose a folder to save the statements to.")
        try:
            sah.load_logo(sah.BRANDING)
            sah.load_provider(sah.BRANDING)
        except sah.BrandingError as ex:
            problems.append(f"{ex}\nFix or remove the file in the branding folder:\n{sah.BRANDING}")
        if problems:
            messagebox.showwarning("Please fix these first", "\n\n".join(problems))
            return
        save_settings({"clients": clients, "items": items, "outdir": outdir})
        self.rows.delete(0, "end")
        self.bar.configure(value=0, maximum=1)
        self.status.set("Starting…")
        self.cancel = threading.Event()
        self.worker = threading.Thread(target=self.work, args=(clients, items, outdir, self.cancel), daemon=True)
        self.worker.start()
        self.refresh_buttons()

    def work(self, clients, items, outdir, cancel):
        """Background thread. Talks to the window only through self.q."""
        try:
            summary = sah.run(clients, items, outdir, on_progress=lambda p: self.q.put(("progress", p)), cancel_event=cancel)
            self.q.put(("finished", summary))
        except sah.BrandingError as ex:
            self.q.put(("problem", str(ex)))
        except PermissionError as ex:
            self.q.put(("problem", f"Windows didn't allow access to a file. If it's open in Excel or a PDF viewer, close it and try again.\n\n{ex.filename or ex}"))
        except Exception:
            self.q.put(("crash", traceback.format_exc()))

    def request_cancel(self):
        if self.running():
            self.cancel.set()
            self.status.set("Stopping after the current statement…")
            self.refresh_buttons()

    def poll(self):
        try:
            while not self.closed:
                kind, data = self.q.get_nowait()
                getattr(self, "on_" + kind)(data)
        except queue.Empty:
            pass
        except Exception:
            show_crash(traceback.format_exc())
        if not self.closed:
            self.root.after(100, self.poll)

    def on_progress(self, p):
        if p["ok"]:
            line = f'{p["name"]} ({p["client_id"]}), {p["pages"]} pages, done'
        else:
            line = f'{p["name"]} ({p["client_id"]}), FAILED - {p["error"]}'
        self.rows.insert("end", line)
        if not p["ok"]:
            self.rows.itemconfig("end", foreground=RED, selectforeground=RED)
        if self.rows.size() > MAX_ROWS:
            self.rows.delete(0)
        self.rows.see("end")
        self.bar.configure(maximum=max(p["total"], 1), value=p["index"])
        if self.cancel.is_set():
            return   # keep "Stopping…" visible
        left = p["elapsed_seconds"] / p["index"] * (p["total"] - p["index"])
        self.status.set(f'{p["done_count"]:,} of {p["total"]:,} statements created · {p["failed_count"]:,} failed · {time_left(left)}')

    def end_run(self):
        self.worker.join()
        if self.closing:
            self.closed = True
            self.root.destroy()
            return False
        self.refresh_buttons()
        return True

    def on_finished(self, s):
        if not self.end_run():
            return
        msg = f'{s["done"]:,} statements created, {s["failed"]:,} failed, in {sah.fmt_t(s["elapsed"])}'
        if s["cancelled"]:
            not_started = s["total"] - s["done"] - s["failed"]
            self.status.set(f"Stopped. {msg}.")
            messagebox.showinfo("Stopped", f"Stopped. {msg}.\n{not_started:,} statements were not started.")
        else:
            if s["total"]:
                self.bar.configure(maximum=s["total"], value=s["total"])
            self.status.set(f"Finished. {msg}.")
            extra = "\n\nFailed rows are listed in red and in the error log." if s["failed"] else ""
            messagebox.showinfo("Finished", msg + "." + extra)

    def on_problem(self, text):
        if self.end_run():
            self.status.set("Not finished - see the message.")
            messagebox.showerror("Couldn't create statements", text)

    def on_crash(self, text):
        if self.end_run():
            self.status.set("Not finished - something went wrong.")
            show_crash(text)

    def on_close(self):
        if not self.running():
            self.root.destroy()
        elif messagebox.askyesno("Close", "A run is in progress. Stop and close?", icon="warning"):
            self.closing = True
            self.request_cancel()   # window closes when the current statement finishes (see end_run)


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    sys.excepthook = lambda t, v, tb: log_crash("".join(traceback.format_exception(t, v, tb)))
    threading.excepthook = lambda a: log_crash("".join(traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback)))
    root = tk.Tk()
    root.report_callback_exception = lambda t, v, tb: show_crash("".join(traceback.format_exception(t, v, tb)))
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
