# gui.py
import tkinter as tk
from pathlib import Path
from queue import Queue, Empty
from tkinter import ttk, scrolledtext, messagebox, filedialog
from typing import Dict, List

import config
import utils
from core import GamdlCore
from settings import SettingsManager


class GamdlGUI:
    def __init__(self, root: tk.Tk):
        """Initializes the GUI, Managers, and builds the layout."""
        self.root = root
        self.queue: Queue = Queue()

        # 1. Initialize logic & persistence
        self.settings = SettingsManager()
        self.core = GamdlCore(self.queue)

        # 2. Load state
        self.user_prefs = self.settings.load()
        self.current_theme = self.user_prefs.get("theme", "light")

        # Placeholder state flags
        self.is_folder_ph = False
        self.is_cookie_ph = False

        # UI Element Collections (for theming)
        self.ui_elements: Dict[str, List[tk.Widget]] = {
            "main_bg": [], "card_bg": [], "text": [],
            "inputs": [], "dividers": [], "std_frames": []
        }

        # 3. Build UI
        self._init_window()
        self._create_widgets()
        self._apply_theme()
        self._restore_inputs()

        # 4. Start Loops
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_queue)  # Log consumer loop
        self.root.after(200, self.core.check_environment)  # Initial check

    def _init_window(self) -> None:
        """Sets window title, size, and menu."""
        self.root.title("Apple Music Downloader")
        self.root.geometry(config.WINDOW_SIZE)
        self.root.minsize(*config.MIN_SIZE)
        self._create_menu()

    def _create_menu(self) -> None:
        """Builds the top menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Downloads Folder", command=self._open_dl_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        # Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Update Gamdl", command=self._update_gamdl)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", "Gamdl GUI v2.0"))
        menubar.add_cascade(label="Help", menu=help_menu)

    def _create_widgets(self) -> None:
        """Constructs all visual elements on the screen."""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        pad_frame = tk.Frame(main_frame)
        pad_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.ui_elements["main_bg"].append(pad_frame)

        # Header
        header = tk.Frame(pad_frame)
        header.pack(fill=tk.X, pady=(0, 15))
        self.ui_elements["main_bg"].append(header)

        title = tk.Label(header, text="Music Downloader", font=config.FONT_TITLE, anchor="w")
        title.pack(side=tk.LEFT)
        self.ui_elements["text"].append(title)

        ver = tk.Label(header, text="v2.0", font=config.FONT_UI)
        ver.pack(side=tk.LEFT, padx=10, anchor="s", pady=(0, 4))
        self.ui_elements["text"].append(ver)

        self.theme_btn = tk.Button(header, text="☾", font=("Segoe UI", 12), bd=0, cursor="hand2",
                                   command=self._toggle_theme, relief="flat")
        self.theme_btn.pack(side=tk.RIGHT)
        self.ui_elements["main_bg"].append(self.theme_btn)

        # Inputs
        self._create_card(pad_frame, "Link to album or track:", is_url=True)
        self._create_settings_card(pad_frame)

        # Actions
        btn_box = tk.Frame(pad_frame)
        btn_box.pack(fill=tk.X, pady=(0, 20))
        self.ui_elements["main_bg"].append(btn_box)

        self.btn_dl = tk.Button(btn_box, text="DOWNLOAD MUSIC", font=config.FONT_BOLD, bd=0, cursor="hand2",
                                command=self._start_download, relief="flat")
        self.btn_dl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)

        self.btn_stop = tk.Button(btn_box, text="STOP", font=config.FONT_BOLD, bd=0, cursor="hand2",
                                  command=self.core.stop_download, relief="flat", state=tk.DISABLED)
        self.btn_stop.pack(side=tk.RIGHT, ipady=8, ipadx=20)

        # Feedback
        self.prog_var = tk.DoubleVar()
        self.prog_bar = ttk.Progressbar(pad_frame, orient="horizontal", mode="determinate", variable=self.prog_var)
        self.prog_bar.pack(fill=tk.X)

        self.log_area = scrolledtext.ScrolledText(pad_frame, state='disabled', height=10, font=config.FONT_LOG,
                                                  relief="flat", bd=0, padx=10, pady=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, font=("Segoe UI", 8), anchor="w", padx=15,
                                   pady=3)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _create_settings_card(self, parent: tk.Widget) -> None:
        """Helper to build the Settings card layout."""
        card = tk.Frame(parent, bd=0, highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 15))
        self.ui_elements["std_frames"].append(card)
        card.columnconfigure(1, weight=1)

        # 1. Format
        tk.Label(card, text="Format", font=config.FONT_BOLD, width=10, anchor="w").grid(row=0, column=0, padx=15,
                                                                                        pady=12)
        self.codec_var = tk.StringVar()
        self.codec_combo = ttk.Combobox(card, textvariable=self.codec_var, state="readonly", font=config.FONT_UI)
        self.codec_combo['values'] = list(config.CODEC_MAP.keys())
        self.codec_combo.current(0)
        self.codec_combo.grid(row=0, column=1, columnspan=3, sticky="ew", padx=15, pady=12)

        self._add_divider(card, 1)

        # 2. Folder
        tk.Label(card, text="Folder", font=config.FONT_BOLD, width=10, anchor="w").grid(row=2, column=0, padx=15,
                                                                                        pady=12)
        self.ent_folder = tk.Entry(card, font=config.FONT_UI, bd=0, relief="flat")
        self.ent_folder.grid(row=2, column=1, sticky="ew", pady=12)
        self.ui_elements["inputs"].append(self.ent_folder)

        tk.Button(card, text="•••", bd=0, cursor="hand2", font=config.FONT_BOLD,
                  command=self._browse_folder).grid(row=2, column=2, padx=5)
        tk.Button(card, text="📂", bd=0, cursor="hand2", font=("Segoe UI", 10),
                  command=self._open_dl_folder).grid(row=2, column=3, padx=(0, 15))

        self._add_divider(card, 3)

        # 3. Cookies
        tk.Label(card, text="Cookies", font=config.FONT_BOLD, width=10, anchor="w").grid(row=4, column=0, padx=15,
                                                                                         pady=12)
        self.ent_cookies = tk.Entry(card, font=config.FONT_UI, bd=0, relief="flat")
        self.ent_cookies.grid(row=4, column=1, sticky="ew", pady=12)
        self.ui_elements["inputs"].append(self.ent_cookies)

        tk.Button(card, text="•••", bd=0, cursor="hand2", font=config.FONT_BOLD,
                  command=self._browse_cookies).grid(row=4, column=2, padx=5)
        tk.Button(card, text="📂", bd=0, cursor="hand2", font=("Segoe UI", 10),
                  command=self._open_cookie_folder).grid(row=4, column=3, padx=(0, 15))

        # Events
        self.ent_folder.bind("<FocusIn>", lambda e: self._on_focus(True, True))
        self.ent_folder.bind("<FocusOut>", lambda e: self._on_focus(False, True))
        self.ent_cookies.bind("<FocusIn>", lambda e: self._on_focus(True, False))
        self.ent_cookies.bind("<FocusOut>", lambda e: self._on_focus(False, False))

    def _create_card(self, parent: tk.Widget, title: str, is_url: bool = False) -> None:
        """Helper to build a standard Input card."""
        card = tk.Frame(parent, bd=0, highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 15))
        self.ui_elements["std_frames"].append(card)

        tk.Label(card, text=title, font=config.FONT_BOLD, anchor="w").pack(fill=tk.X, padx=15, pady=(12, 5))

        wrapper = tk.Frame(card, bd=0)
        wrapper.pack(fill=tk.X, padx=15, pady=(0, 15))
        self.url_wrapper = wrapper  # Reference for theming

        entry = tk.Entry(wrapper, font=("Segoe UI", 11), bd=0, relief="flat")
        entry.pack(fill=tk.X, padx=1, pady=1, ipady=6)
        if is_url: self.ent_url = entry
        self.ui_elements["inputs"].append(entry)

    def _add_divider(self, parent: tk.Widget, row: int) -> None:
        """Adds a 1px horizontal line."""
        div = tk.Frame(parent, height=1)
        div.grid(row=row, column=0, columnspan=4, sticky="ew", padx=15)
        self.ui_elements["dividers"].append(div)

    # --- Event Loop Consumer ---

    def _poll_queue(self) -> None:
        """
        Periodically checks the queue for messages from Core and updates UI.
        Runs approx every 50ms.
        """
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == "LOG":
                    self._log(data[0], data[1])
                elif msg_type == "PROGRESS":
                    self.prog_var.set(data)
                elif msg_type == "STATUS":
                    self.status_var.set(data)
                elif msg_type == "MSG_BOX":
                    messagebox.showinfo(data[0], data[1])
        except Empty:
            pass
        self.root.after(50, self._poll_queue)

    # --- Actions ---

    def _start_download(self) -> None:
        """Validates input and tells Core to start."""
        url = self.ent_url.get().strip()

        if not self.core.validate_request(url):
            return

            # Determine actual paths (handle placeholders)
        folder = self.core.default_music_folder if self.is_folder_ph else Path(self.ent_folder.get())

        if self.is_cookie_ph:
            if self.core.doc_cookies_path.exists():
                cookies = self.core.doc_cookies_path
            elif self.core.local_cookies_path.exists():
                cookies = self.core.local_cookies_path
            else:
                messagebox.showerror("Error", "No cookies file found!")
                return
        else:
            cookies = Path(self.ent_cookies.get())

        if not folder.exists():
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create folder: {e}")
                return

        if not cookies.exists():
            messagebox.showerror("Error", "Cookies file not found")
            return

        # Lock UI
        self.btn_dl.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.ent_url.delete(0, tk.END)

        # Execute
        self.core.run_download(url, folder, cookies, self.codec_combo.get(), self._on_finish)

    def _on_finish(self) -> None:
        """Unlock UI buttons (Called from thread via lambda or poll)."""
        self.root.after(0, lambda: [
            self.btn_dl.config(state=tk.NORMAL),
            self.btn_stop.config(state=tk.DISABLED)
        ])

    def _update_gamdl(self) -> None:
        """Trigger update logic in Core."""
        if messagebox.askyesno("Update", "Update gamdl via pip?"):
            self.btn_dl.config(state=tk.DISABLED)
            self.core.update_gamdl(self._on_finish)

    def _log(self, text: str, tag: str) -> None:
        """Inserts text into the scrollable log area."""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"{text}\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    # --- File System Helpers ---

    def _browse_folder(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.ent_folder.delete(0, tk.END)
            self.ent_folder.insert(0, path.replace("/", "\\"))
            self.is_folder_ph = False
            self._update_ph_colors()

    def _browse_cookies(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Txt", "*.txt")])
        if path:
            self.ent_cookies.delete(0, tk.END)
            self.ent_cookies.insert(0, path)
            self.is_cookie_ph = False
            self._update_ph_colors()

    def _open_dl_folder(self) -> None:
        path = self.core.default_music_folder if self.is_folder_ph else Path(self.ent_folder.get())
        try:
            utils.open_path_in_os(path)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_cookie_folder(self) -> None:
        if self.is_cookie_ph:
            if self.core.doc_cookies_path.exists():
                path = self.core.doc_cookies_path
            elif self.core.local_cookies_path.exists():
                path = self.core.local_cookies_path
            else:
                return
        else:
            path = Path(self.ent_cookies.get())
        try:
            utils.open_path_in_os(path.parent)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # --- Persistence & Placeholders ---

    def _restore_inputs(self) -> None:
        """Restores last used paths/codec from settings."""
        if c := self.user_prefs.get("codec_label"): self.codec_combo.set(c)

        if p := self.user_prefs.get("download_path"):
            self.ent_folder.insert(0, p)
        else:
            self.is_folder_ph = True
            self.ent_folder.insert(0, str(self.core.default_music_folder))

        if c := self.user_prefs.get("cookies_path"):
            self.ent_cookies.insert(0, c)
        else:
            self.is_cookie_ph = True
            val = self.core.doc_cookies_path if self.core.doc_cookies_path.exists() else self.core.local_cookies_path
            self.ent_cookies.insert(0, str(val))

        self._update_ph_colors()

    def _on_close(self) -> None:
        """Saves settings and kills processes on exit."""
        self.core.stop_download()
        data = {
            "codec_label": self.codec_combo.get(),
            "download_path": self.ent_folder.get() if not self.is_folder_ph else "",
            "cookies_path": self.ent_cookies.get() if not self.is_cookie_ph else "",
            "theme": self.current_theme
        }
        self.settings.save(data)
        self.root.destroy()

    def _on_focus(self, is_in: bool, is_folder: bool) -> None:
        """Handles placeholder text logic (ghost text)."""
        entry = self.ent_folder if is_folder else self.ent_cookies
        flag = self.is_folder_ph if is_folder else self.is_cookie_ph

        if is_in and flag:
            entry.delete(0, tk.END)
            if is_folder:
                self.is_folder_ph = False
            else:
                self.is_cookie_ph = False
        elif not is_in and not entry.get().strip():
            val = str(self.core.default_music_folder) if is_folder else str(self.core.doc_cookies_path)
            entry.insert(0, val)
            if is_folder:
                self.is_folder_ph = True
            else:
                self.is_cookie_ph = True
        self._update_ph_colors()

    # --- Theming ---

    def _toggle_theme(self) -> None:
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Applies colors from config.THEMES to all UI elements."""
        c = config.THEMES[self.current_theme]
        self.root.configure(bg=c["bg"])
        self.theme_btn.config(text="☀" if self.current_theme == "dark" else "☾")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=c["bg"])
        style.configure("Horizontal.TProgressbar", troughcolor=c["bg"], background=c["accent"], borderwidth=0,
                        thickness=2)
        style.map("TCombobox", fieldbackground=[("readonly", c["card_bg"])],
                  selectbackground=[("readonly", c["card_bg"])], foreground=[("readonly", c["fg"])],
                  selectforeground=[("readonly", c["fg"])])

        for w in self.ui_elements["main_bg"]: w.config(bg=c["bg"])

        self.btn_dl.config(bg=c["accent"], fg=c["accent_fg"], activebackground="#D41E33", activeforeground="white")
        self.btn_stop.config(bg=c["stop_bg"], fg=c["stop_fg"], activebackground=c["stop_bg"], activeforeground=c["fg"])
        self.theme_btn.config(fg=c["fg"], activebackground=c["bg"], activeforeground=c["accent"])
        self.status_bar.config(bg=c["bg"], fg=c["sub_fg"])
        self.url_wrapper.config(bg=c["input_border"])

        for w in self.ui_elements["std_frames"]:
            w.config(bg=c["card_bg"], highlightbackground=c["card_border"], highlightcolor=c["card_border"])
            for child in w.winfo_children():
                if isinstance(child, tk.Label): child.config(bg=c["card_bg"], fg=c["fg"])
                if isinstance(child, tk.Button): child.config(bg=c["card_bg"], fg=c["fg"],
                                                              activebackground=c["card_bg"],
                                                              activeforeground=c["accent"])

        for div in self.ui_elements["dividers"]: div.config(bg=c["divider"])

        self.log_area.config(bg=c["log_bg"], fg=c["log_fg"], selectbackground=c["accent"])
        self.log_area.tag_config("green", foreground="#32D74B" if self.current_theme == "dark" else "#34C759")
        self.log_area.tag_config("red", foreground="#FF453A" if self.current_theme == "dark" else "#FF3B30")
        self.log_area.tag_config("cyan", foreground="#64D2FF" if self.current_theme == "dark" else "#007AFF")
        self.log_area.tag_config("yellow", foreground="#FFD60A" if self.current_theme == "dark" else "#FFCC00")
        self.log_area.tag_config("header", foreground=c["bg"], background=c["fg"])

        self._update_ph_colors()

    def _update_ph_colors(self) -> None:
        """Updates input field colors based on whether they contain placeholder text."""
        c = config.THEMES[self.current_theme]

        def set_col(ent, is_ph):
            ent.config(bg=c["card_bg"], fg=c["placeholder"] if is_ph else c["entry_fg"], insertbackground=c["fg"])

        set_col(self.ent_folder, self.is_folder_ph)
        set_col(self.ent_cookies, self.is_cookie_ph)
        self.ent_url.config(bg=c["card_bg"], fg=c["entry_fg"], insertbackground=c["fg"])