import os
import sys
import subprocess
import threading
import tkinter as tk
import time
import re
import shutil
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path

# =================================================================================
# CONSTANTS & CONFIGURATION
# =================================================================================

WINDOW_SIZE = "720x680"
MIN_SIZE = (680, 600)
FONT_UI = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_LOG = ("Consolas", 9)

THEMES = {
    "light": {
        "bg": "#F2F2F7",  # SystemGray6
        "card_bg": "#FFFFFF",  # Card background
        "card_border": "#E5E5EA",  # Card border
        "fg": "#000000",  # Main text
        "sub_fg": "#8E8E93",  # Secondary text
        "entry_bg": "#FFFFFF",  # Input background
        "entry_fg": "#000000",  # Input text
        "input_border": "#C7C7CC",  # Input border/shadow
        "divider": "#E5E5EA",  # Dividers
        "accent": "#FA233B",  # Apple Red
        "accent_fg": "#FFFFFF",  # Button text
        "log_bg": "#1C1C1E",  # Log background
        "log_fg": "#00FF00",  # Log text
        "placeholder": "#C7C7CC"  # Placeholder color
    },
    "dark": {
        "bg": "#000000",
        "card_bg": "#1C1C1E",
        "card_border": "#2C2C2E",
        "fg": "#FFFFFF",
        "sub_fg": "#98989D",
        "entry_bg": "#1C1C1E",
        "entry_fg": "#FFFFFF",
        "input_border": "#3A3A3C",
        "divider": "#2C2C2E",
        "accent": "#FA233B",
        "accent_fg": "#FFFFFF",
        "log_bg": "#121212",
        "log_fg": "#00FF00",
        "placeholder": "#636366"
    }
}

GAMDL_CONFIG_TEMPLATE = """[gamdl]
save_cover = true
no_synced_lyrics = true
log_level = INFO
log_file = null
no_exceptions = false
language = en-US
wvd_path = null
overwrite = false
save_playlist = false
nm3u8dlre_path = N_m3u8DL-RE
mp4decrypt_path = mp4decrypt
ffmpeg_path = ffmpeg
mp4box_path = MP4Box
download_mode = ytdlp
remux_mode = ffmpeg
cover_format = jpg
album_folder_template = {album_artist}/{album}
compilation_folder_template = Compilations/{album}
single_disc_file_template = {track:02d} {title}
multi_disc_file_template = {disc}-{track:02d} {title}
no_album_folder_template = {artist}/Unknown Album
no_album_file_template = {title}
playlist_file_template = Playlists/{playlist_artist}/{playlist_title}
date_tag_template = %Y-%m-%dT%H:%M:%SZ
exclude_tags = null
cover_size = 1200
truncate = null
synced_lyrics_format = lrc
synced_lyrics_only = false
music_video_codec_priority = h264,h265
music_video_remux_format = m4v
music_video_resolution = 1080p
uploaded_video_quality = best
codec_song = {codec}
cookies_path = {cookies}
"""


class GamdlApp:
    def __init__(self, root):
        self.root = root
        self._setup_window()
        self._init_paths()

        # State
        self.current_theme = "light"
        self.is_folder_placeholder = False
        self.is_cookie_placeholder = False

        # UI Component Lists (for theme updates)
        self.ui_main_bg = []
        self.ui_card_bg = []
        self.ui_inputs = []
        self.ui_text = []
        self.ui_dividers = []
        self.ui_std_frames = []

        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        # Codec Mapping
        self.codec_map = {
            "m4a (AAC - Original)": "aac-legacy",
            "mp3 (Converted)": "mp3"
        }

        self._create_layout()
        self._apply_theme()
        self.root.after(100, self._check_environment)

    def _setup_window(self):
        self.root.title("Apple Music Downloader")
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(*MIN_SIZE)

    def _init_paths(self):
        if getattr(sys, 'frozen', False):
            self.base_dir = Path(sys.executable).parent
        else:
            self.base_dir = Path(__file__).parent.resolve()

        self.temp_config_file = self.base_dir / "temp_config.ini"
        self.doc_cookies_path = Path(os.path.expanduser("~")) / "Documents" / "Apple Music" / "cookies.txt"
        self.local_cookies_path = self.base_dir / "cookies.txt"
        self.default_music_folder = Path(os.path.expanduser("~")) / "Downloads" / "Apple Music Download"

        self.gamdl_exe = shutil.which("gamdl")

    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================
    def _create_layout(self):
        # Main Containers
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.pad_frame = tk.Frame(self.main_frame)
        self.pad_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.ui_main_bg.append(self.pad_frame)

        self._create_header()
        self._create_url_card()
        self._create_settings_card()
        self._create_action_area()
        self._create_log_area()
        self._create_status_bar()
        self._setup_bindings()

    def _create_header(self):
        header = tk.Frame(self.pad_frame)
        header.pack(fill=tk.X, pady=(0, 15))
        self.ui_main_bg.append(header)

        title = tk.Label(header, text="Music Downloader", font=FONT_TITLE, anchor="w")
        title.pack(side=tk.LEFT)
        self.ui_text.append(title)

        self.version_label = tk.Label(header, text="v1.0", font=FONT_UI)
        self.version_label.pack(side=tk.LEFT, padx=10, anchor="s", pady=(0, 4))

        self.theme_btn = tk.Button(header, text="☾", font=("Segoe UI", 12), bd=0, cursor="hand2",
                                   command=self.toggle_theme, relief="flat")
        self.theme_btn.pack(side=tk.RIGHT)
        self.ui_main_bg.append(self.theme_btn)

    def _create_url_card(self):
        # URL Card with thin border
        self.card_url = tk.Frame(self.pad_frame, bd=0, highlightthickness=1)
        self.card_url.pack(fill=tk.X, pady=(0, 15))
        self.ui_std_frames.append(self.card_url)

        lbl = tk.Label(self.card_url, text="Link to album or track:", font=FONT_BOLD, anchor="w")
        lbl.pack(fill=tk.X, padx=15, pady=(12, 5))
        self.ui_card_bg.append(lbl)

        # Wrapper for input border/shadow effect
        self.url_wrapper = tk.Frame(self.card_url, bd=0)
        self.url_wrapper.pack(fill=tk.X, padx=15, pady=(0, 15))

        self.url_entry = tk.Entry(self.url_wrapper, font=("Segoe UI", 11), bd=0, relief="flat")
        self.url_entry.pack(fill=tk.X, padx=1, pady=1, ipady=6)
        self.url_entry.bind('<Return>', lambda e: self.start_download())
        self.ui_inputs.append(self.url_entry)

    def _create_settings_card(self):
        self.card_settings = tk.Frame(self.pad_frame, bd=0, highlightthickness=1)
        self.card_settings.pack(fill=tk.X, pady=(0, 15))
        self.ui_std_frames.append(self.card_settings)
        self.card_settings.columnconfigure(1, weight=1)

        # 1. Format
        self._add_setting_row(0, "Format", is_combo=True)
        self._add_divider(1)
        # 2. Folder
        self._add_setting_row(2, "Folder", btn_cmd=self.browse_folder, is_folder=True)
        self._add_divider(3)
        # 3. Cookies
        self._add_setting_row(4, "Cookies", btn_cmd=self.browse_cookies, is_cookie=True)

    def _add_setting_row(self, row, label_text, btn_cmd=None, is_combo=False, is_folder=False, is_cookie=False):
        lbl = tk.Label(self.card_settings, text=label_text, font=FONT_BOLD, anchor="w", width=10)
        lbl.grid(row=row, column=0, sticky="w", padx=(15, 0), pady=12)
        self.ui_card_bg.append(lbl)

        if is_combo:
            self.codec_var = tk.StringVar()
            self.codec_combo = ttk.Combobox(self.card_settings, textvariable=self.codec_var, state="readonly",
                                            font=FONT_UI)
            self.codec_combo['values'] = list(self.codec_map.keys())
            self.codec_combo.current(0)
            self.codec_combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 15), pady=12)
        else:
            entry = tk.Entry(self.card_settings, font=FONT_UI, bd=0, relief="flat")
            entry.grid(row=row, column=1, sticky="ew", pady=12, ipady=2)
            self.ui_inputs.append(entry)

            if is_folder: self.folder_entry = entry
            if is_cookie: self.cookies_entry = entry

            btn = tk.Button(self.card_settings, text="•••", bd=0, cursor="hand2", command=btn_cmd,
                            font=("Segoe UI", 8, "bold"))
            btn.grid(row=row, column=2, padx=(5, 15), pady=12)

            if is_folder: self.btn_fld = btn
            if is_cookie: self.btn_cook = btn

    def _add_divider(self, row):
        div = tk.Frame(self.card_settings, height=1)
        div.grid(row=row, column=0, columnspan=3, sticky="ew", padx=15)
        self.ui_dividers.append(div)

    def _create_action_area(self):
        self.download_btn = tk.Button(self.pad_frame, text="DOWNLOAD MUSIC", font=("Segoe UI", 11, "bold"), bd=0,
                                      cursor="hand2", command=self.start_download, relief="flat")
        self.download_btn.pack(fill=tk.X, pady=(0, 20), ipady=8)

    def _create_log_area(self):
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.pad_frame, orient="horizontal", mode="determinate",
                                            variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X)

        self.log_area = scrolledtext.ScrolledText(self.pad_frame, state='disabled', height=10, font=FONT_LOG,
                                                  relief="flat", padx=10, pady=10, bd=0)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def _create_status_bar(self):
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, font=("Segoe UI", 8), anchor="w", padx=15,
                                   pady=3)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _setup_bindings(self):
        # Placeholders logic
        for entry, is_fld in [(self.folder_entry, True), (self.cookies_entry, False)]:
            entry.bind("<FocusIn>", lambda e, f=is_fld: self._on_focus(True, f))
            entry.bind("<FocusOut>", lambda e, f=is_fld: self._on_focus(False, f))

        self._set_placeholder(True)

        # Context Menus
        for w in self.ui_inputs: self._bind_context_menu(w, is_readonly=False)
        self._bind_context_menu(self.log_area, is_readonly=True)

    # =========================================================================
    # THEME ENGINE
    # =========================================================================
    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self._apply_theme()

    def _apply_theme(self):
        c = THEMES[self.current_theme]
        self.root.configure(bg=c["bg"])
        self.theme_btn.config(text="☀" if self.current_theme == "dark" else "☾")

        # TTK Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=c["bg"])
        style.configure("Horizontal.TProgressbar", troughcolor=c["bg"], background=c["accent"], borderwidth=0,
                        thickness=2)
        style.map("TCombobox", fieldbackground=[("readonly", c["card_bg"])],
                  selectbackground=[("readonly", c["card_bg"])], foreground=[("readonly", c["fg"])],
                  selectforeground=[("readonly", c["fg"])])
        style.configure("TCombobox", background=c["card_bg"], arrowcolor=c["fg"], borderwidth=0)

        # Batch Updates
        for w in self.ui_main_bg: w.config(bg=c["bg"])
        for w in self.ui_text: w.config(bg=c["bg"], fg=c["fg"])
        for card in self.ui_std_frames: card.config(bg=c["card_bg"], highlightbackground=c["card_border"],
                                                    highlightcolor=c["card_border"])
        for w in self.ui_card_bg: w.config(bg=c["card_bg"], fg=c["fg"] if isinstance(w, tk.Label) else None)
        for div in self.ui_dividers: div.config(bg=c["divider"])

        # Special Elements
        self.url_wrapper.config(bg=c["input_border"])
        self.download_btn.config(bg=c["accent"], fg=c["accent_fg"], activebackground="#D41E33",
                                 activeforeground="white")
        self.version_label.config(bg=c["bg"], fg=c["sub_fg"])
        self.theme_btn.config(fg=c["fg"], activebackground=c["bg"], activeforeground=c["accent"])
        self.status_bar.config(bg=c["bg"], fg=c["sub_fg"])
        self.btn_fld.config(bg=c["card_bg"], fg=c["fg"], activebackground=c["card_bg"], activeforeground=c["accent"])
        self.btn_cook.config(bg=c["card_bg"], fg=c["fg"], activebackground=c["card_bg"], activeforeground=c["accent"])

        # Log
        self.log_area.config(bg=c["log_bg"], fg=c["log_fg"], selectbackground=c["accent"])
        self._update_log_tags(c)

        # Inputs & Placeholders
        self._update_input_colors()

    def _update_log_tags(self, c):
        is_dark = self.current_theme == "dark"
        self.log_area.tag_config("green", foreground="#32D74B" if is_dark else "#34C759")
        self.log_area.tag_config("red", foreground="#FF453A" if is_dark else "#FF3B30")
        self.log_area.tag_config("cyan", foreground="#64D2FF" if is_dark else "#007AFF")
        self.log_area.tag_config("yellow", foreground="#FFD60A" if is_dark else "#FFCC00")
        self.log_area.tag_config("header", foreground=c["bg"], background=c["fg"])

    def _update_input_colors(self):
        c = THEMES[self.current_theme]
        for entry in self.ui_inputs:
            is_ph = (entry == self.folder_entry and self.is_folder_placeholder) or \
                    (entry == self.cookies_entry and self.is_cookie_placeholder)

            # For url_entry bg matches parent wrapper, for others card_bg
            bg_col = c["card_bg"]
            entry.config(bg=bg_col, fg=c["placeholder"] if is_ph else c["entry_fg"], insertbackground=c["fg"])

    # =========================================================================
    # LOGIC: PLACEHOLDERS & HELPERS
    # =========================================================================
    def _on_focus(self, is_in, is_folder):
        entry = self.folder_entry if is_folder else self.cookies_entry
        flag = self.is_folder_placeholder if is_folder else self.is_cookie_placeholder

        if is_in and flag:
            entry.delete(0, tk.END)
            self._set_flag(is_folder, False)
        elif not is_in and not entry.get().strip():
            self._set_placeholder(is_folder)
        self._update_input_colors()

    def _set_placeholder(self, is_folder):
        entry = self.folder_entry if is_folder else self.cookies_entry
        val = str(self.default_music_folder) if is_folder else str(self.doc_cookies_path)
        entry.delete(0, tk.END)
        entry.insert(0, val)
        self._set_flag(is_folder, True)
        self._update_input_colors()

    def _set_flag(self, is_folder, val):
        if is_folder:
            self.is_folder_placeholder = val
        else:
            self.is_cookie_placeholder = val

    def _bind_context_menu(self, widget, is_readonly):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        if not is_readonly:
            menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All",
                         command=lambda: widget.tag_add("sel", "1.0", "end") if is_readonly else widget.select_range(0,
                                                                                                                     'end'))

        def on_key(e):
            ctrl = (e.state & 0x0004) or (e.state & 0x20000)
            if ctrl:
                if e.keycode == 86 and not is_readonly:
                    widget.event_generate("<<Paste>>")
                elif e.keycode == 67:
                    widget.event_generate("<<Copy>>")
                elif e.keycode == 65:
                    if is_readonly:
                        widget.tag_add("sel", "1.0", "end")
                    else:
                        widget.select_range(0, 'end')
                    return "break"

        widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        widget.bind("<Control-Key>", on_key)

    # =========================================================================
    # CORE LOGIC
    # =========================================================================
    def _check_environment(self):
        self._log("--- SYSTEM CHECK ---")
        if self.gamdl_exe:
            self._log(f"[OK] Gamdl found: {self.gamdl_exe}", "green")
        else:
            self._log("[ERROR] Gamdl not found in PATH! Install it via pip.", "red")

        self._check_tool("ffmpeg")
        self._check_tool("mp4decrypt")

        # Cookies Logic
        if self.doc_cookies_path.exists():
            self._set_flag(False, False)
            self.cookies_entry.delete(0, tk.END)
            self.cookies_entry.insert(0, str(self.doc_cookies_path))
            self._log(f"[OK] Cookies found: {self.doc_cookies_path}", "green")
        elif self.local_cookies_path.exists():
            self._set_flag(False, False)
            self.cookies_entry.delete(0, tk.END)
            self.cookies_entry.insert(0, str(self.local_cookies_path))
            self._log(f"[OK] Cookies found: {self.local_cookies_path}", "green")
        else:
            self._set_placeholder(False)
            self._log("[WARNING] cookies.txt not found.", "yellow")

        self._update_input_colors()
        if self.gamdl_exe: self._log("--------------------------\n")

    def _check_tool(self, name):
        if shutil.which(name) or (self.base_dir / f"{name}.exe").exists():
            self._log(f"[OK] {name} found.", "green")
        else:
            self._log(f"[WARNING] {name} not found.", "yellow")

    def browse_folder(self):
        path = filedialog.askdirectory(initialdir=self.get_target_folder())
        if path:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, path.replace("/", "\\"))
            self._set_flag(True, False)
            self._update_input_colors()

    def browse_cookies(self):
        path = filedialog.askopenfilename(filetypes=[("Txt", "*.txt")], initialdir=self.base_dir)
        if path:
            self.cookies_entry.delete(0, tk.END)
            self.cookies_entry.insert(0, path)
            self._set_flag(False, False)
            self._update_input_colors()

    def get_target_folder(self):
        if self.is_folder_placeholder: return self.default_music_folder
        return Path(self.folder_entry.get().strip())

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url or not self.gamdl_exe:
            if not url: messagebox.showinfo("Info", "Enter a link")
            return

        target = self.get_target_folder()
        if not target.exists():
            try:
                target.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self._log(f"[ERROR] Folder creation error: {e}", "red")
                return

        cookies_val = self.cookies_entry.get().strip()
        if self.is_cookie_placeholder or not os.path.exists(cookies_val):
            self._log("[ERROR] Cookies file not found!", "red")
            return

        cookie_path = Path(cookies_val).resolve().as_posix()
        selected_codec = self.codec_combo.get()
        # Use codec_map to get internal value, fallback to mp3 if not found
        codec = self.codec_map.get(selected_codec, "mp3")

        cfg_content = GAMDL_CONFIG_TEMPLATE.format(codec=codec, cookies=cookie_path)
        with open(self.temp_config_file, "w", encoding="utf-8") as f:
            f.write(cfg_content)

        self.download_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("Downloading...")
        self.url_entry.delete(0, tk.END)

        threading.Thread(target=self._run_process, args=(url, target, cookie_path), daemon=True).start()

    def _run_process(self, url, target, cookies):
        self.root.after(0, lambda: self._log("\n\n=========================================", "header"))
        self.root.after(0, lambda: self._log(f" Starting: {url}", "header"))
        self.root.after(0, lambda: self._log("=========================================\n"))

        cmd = [self.gamdl_exe, "--config-path", str(self.temp_config_file),
               "--cookies-path", cookies, "--output-path", str(target), url]

        env = os.environ.copy()
        env.update({"PYTHONUNBUFFERED": "1", "TERM": "dumb", "NO_COLOR": "1"})

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        log_file = self.base_dir / "gamdl_output.log"

        try:
            with open(log_file, "w", encoding="utf-8") as writer:
                proc = subprocess.Popen(cmd, stdout=writer, stderr=writer, stdin=subprocess.DEVNULL,
                                        cwd=self.base_dir, startupinfo=si, env=env)

            with open(log_file, "r", encoding="utf-8", errors="replace") as reader:
                while True:
                    line = reader.readline()
                    if not line:
                        if proc.poll() is not None:
                            for l in reader.readlines(): self._process_log(l.strip())
                            break
                        time.sleep(0.1)
                    else:
                        self._process_log(line.strip())

            if proc.returncode == 0:
                self.root.after(0, lambda: [self.progress_var.set(100), self.status_var.set("Done"),
                                            messagebox.showinfo("Success", "Download complete!")])
            else:
                self.root.after(0, lambda: [self.status_var.set("Error"), self._log(f"Code: {proc.returncode}", "red")])

        except Exception as e:
            self.root.after(0, lambda: self._log(f"Launch error: {e}", "red"))
        finally:
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))

    def _process_log(self, line):
        if not line: return
        clean = self.ansi_escape.sub('', line)

        if "[download]" in clean:
            if match := re.search(r'(\d+\.?\d*)%', clean):
                try:
                    self.root.after(0, lambda: self.progress_var.set(float(match.group(1))))
                except:
                    pass
            if "100%" in clean or "Destination" in clean:
                self.root.after(0, self._log, f"        {clean}", "cyan")
            return

        tag = "green" if any(x in clean for x in ["INFO", "Downloading", "Finished", "Processing"]) else \
            "yellow" if "WARNING" in clean else \
                "red" if "ERROR" in clean or "Traceback" in clean else None

        prefix = "\n" if "Processing" in clean or "Finished" in clean else "    " if "Downloading" in clean else ""
        self.root.after(0, self._log, f"{prefix}{clean}", tag)

    def _log(self, msg, tag=None):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"{msg}\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    try:
        style = ttk.Style()
        style.theme_use('clam')
    except:
        pass
    app = GamdlApp(root)
    root.mainloop()