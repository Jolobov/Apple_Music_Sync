# core.py
import os
import sys
import shutil
import subprocess
import threading
import re
from pathlib import Path
from typing import Optional, Callable
from queue import Queue

import config
import utils


class GamdlCore:
    def __init__(self, log_queue: Queue):
        """
        Initializes the Core logic engine.

        Args:
            log_queue: A thread-safe queue to push logs, progress updates, and status messages to the UI.
        """
        self.log_queue = log_queue
        self.current_process: Optional[subprocess.Popen] = None

        self.base_dir = utils.get_base_dir()
        self.temp_config_file = self.base_dir / "temp_config.ini"

        # Default paths logic
        self.doc_cookies_path = Path(os.path.expanduser("~")) / "Documents" / "Apple Music" / "cookies.txt"
        self.local_cookies_path = self.base_dir / "cookies.txt"
        self.default_music_folder = Path(os.path.expanduser("~")) / "Downloads" / "Apple Music Download"

        self.gamdl_exe = utils.get_tool_path("gamdl", self.base_dir)

    def _emit(self, msg_type: str, data: any) -> None:
        """Helper to push messages to the queue."""
        self.log_queue.put((msg_type, data))

    def log(self, msg: str, tag: Optional[str] = None) -> None:
        """Sends a log line to the UI."""
        self._emit("LOG", (msg, tag))

    def set_progress(self, value: float) -> None:
        """Sends a progress bar update (0-100)."""
        self._emit("PROGRESS", value)

    def set_status(self, text: str) -> None:
        """Updates the status bar text."""
        self._emit("STATUS", text)

    def check_environment(self) -> None:
        """
        Performs initial system checks (tools, paths) and logs results to the UI.
        Should be called after UI is ready.
        """
        self.log("--- SYSTEM CHECK ---")

        # 1. Check Gamdl
        if self.gamdl_exe != "gamdl" or shutil.which("gamdl"):
            self.log(f"[OK] Gamdl found: {self.gamdl_exe}", "green")
        else:
            self.log("[ERROR] Gamdl not found in PATH! Install via pip.", "red")

        # 2. Check dependencies
        for tool in ["ffmpeg", "mp4decrypt"]:
            path = utils.get_tool_path(tool, self.base_dir)
            if os.path.isabs(path) or shutil.which(path):
                self.log(f"[OK] {tool} found.", "green")
            else:
                self.log(f"[WARNING] {tool} not found.", "yellow")

        # 3. Check Cookies presence
        if self.doc_cookies_path.exists():
            self.log(f"[OK] Auto-detected cookies: {self.doc_cookies_path}", "green")
        elif self.local_cookies_path.exists():
            self.log(f"[OK] Auto-detected cookies: {self.local_cookies_path}", "green")
        else:
            self.log("[WARNING] cookies.txt not found. Please select manually.", "yellow")

        self.log("--------------------------\n")

    def validate_request(self, url: str) -> bool:
        """
        Validates input data before starting a download.

        Returns:
            True if valid, False otherwise (errors are logged internally).
        """
        if not url:
            self._emit("MSG_BOX", ("Info", "Enter a link"))
            return False

        if not self.gamdl_exe:
            self._emit("MSG_BOX", ("Error", "Gamdl executable missing"))
            return False

        if "music.apple.com" not in url:
            self._emit("MSG_BOX", ("Invalid Link", "Must be an Apple Music link."))
            return False

        return True

    def run_download(self, url: str, folder: Path, cookies: Path, codec_key: str,
                     on_finish: Callable[[], None]) -> None:
        """
        Starts the download process in a separate background thread.

        Args:
            url: The Apple Music URL.
            folder: Target directory path.
            cookies: Path to cookies.txt.
            codec_key: User selected format label (from config.CODEC_MAP).
            on_finish: Callback function to run when thread ends (e.g. to unlock UI).
        """
        thread = threading.Thread(
            target=self._download_task,
            args=(url, folder, cookies, codec_key, on_finish),
            daemon=True
        )
        thread.start()

    def _download_task(self, url: str, folder: Path, cookies: Path, codec_key: str, on_finish: Callable) -> None:
        """The main worker logic. Generates config, runs subprocess, parses output."""
        self.log("\n\n=========================================", "header")
        self.log(f" Starting: {url}", "header")
        self.log("=========================================\n")
        self.set_progress(0)
        self.set_status("Downloading...")

        codec = config.CODEC_MAP.get(codec_key, "mp3")

        try:
            # 1. Generate Config
            cfg_content = config.GAMDL_CONFIG_TEMPLATE.replace("{codec}", codec) \
                .replace("{cookies}", str(cookies).replace("\\", "/")) \
                .replace("{ffmpeg}", utils.get_tool_path("ffmpeg", self.base_dir)) \
                .replace("{decrypt}", utils.get_tool_path("mp4decrypt", self.base_dir)) \
                .replace("{nm3u8}", utils.get_tool_path("N_m3u8DL-RE", self.base_dir)) \
                .replace("{mp4box}", utils.get_tool_path("MP4Box", self.base_dir))

            with open(self.temp_config_file, "w", encoding="utf-8") as f:
                f.write(cfg_content)

            # 2. Prepare Command
            cmd = [
                self.gamdl_exe,
                "--config-path", str(self.temp_config_file),
                "--cookies-path", str(cookies),
                "--output-path", str(folder),
                url
            ]

            # 3. Run Subprocess
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                cwd=self.base_dir,
                startupinfo=utils.get_startup_info(),
                env=utils.get_subprocess_env(),
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            # 4. Stream Logs
            for line in self.current_process.stdout:
                self._parse_log_line(line.strip())

            self.current_process.wait()
            rc = self.current_process.returncode

            # 5. Handle Exit Code
            if rc == 0:
                self.set_progress(100)
                self.set_status("Done")
                self.log("\n[SUCCESS] Finished.", "green")
                self._emit("MSG_BOX", ("Success", "Download complete!"))
            elif rc in [-15, 15, 1]:  # 15 = SIGTERM
                self.set_status("Cancelled")
                self.log("\n[STOP] Cancelled by user.", "red")
            else:
                self.set_status("Error")
                self.log(f"\n[ERROR] Exit code: {rc}", "red")

        except Exception as e:
            self.log(f"[CRITICAL ERROR] {e}", "red")

        finally:
            self.current_process = None
            if self.temp_config_file.exists():
                try:
                    os.remove(self.temp_config_file)
                except:
                    pass

            # Notify UI to unlock
            on_finish()

    def _parse_log_line(self, line: str) -> None:
        """Analyzes a log line to extract progress % or colorize text."""
        if not line: return
        clean = utils.clean_ansi(line)

        if "[download]" in clean:
            if match := re.search(r'(\d+\.?\d*)%', clean):
                try:
                    self.set_progress(float(match.group(1)))
                except ValueError:
                    pass
            if "100%" in clean or "Destination" in clean:
                self.log(f"        {clean}", "cyan")
            return

        tag = "green" if any(x in clean for x in ["INFO", "Downloading", "Finished", "Processing"]) else \
            "yellow" if "WARNING" in clean else \
                "red" if "ERROR" in clean or "Traceback" in clean else None

        prefix = "\n" if "Processing" in clean or "Finished" in clean else "    " if "Downloading" in clean else ""
        self.log(f"{prefix}{clean}", tag)

    def stop_download(self) -> None:
        """Sends SIGTERM to the active process."""
        if self.current_process and self.current_process.poll() is None:
            self.log("\n[STOP] Cancellation requested...", "red")
            self.set_status("Stopping...")
            try:
                self.current_process.terminate()
            except Exception as e:
                self.log(f"[ERROR] Could not stop: {e}", "red")

    def update_gamdl(self, on_finish: Callable[[], None]) -> None:
        """Runs pip install --upgrade gamdl in a background thread."""

        def _update_task():
            self.log("\n--- UPDATING GAMDL ---\n", "header")
            try:
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "gamdl"]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    startupinfo=utils.get_startup_info(),
                    text=True, encoding='utf-8', errors='replace'
                )
                for line in proc.stdout:
                    self.log(f"    {line.strip()}", "green")
                proc.wait()

                if proc.returncode == 0:
                    self.log("--- UPDATE FINISHED ---\n", "header")
                    self._emit("MSG_BOX", ("Success", "Gamdl updated!"))
                    # Re-detect path in case it moved
                    self.gamdl_exe = utils.get_tool_path("gamdl", self.base_dir)
                else:
                    self.log(f"Update failed code {proc.returncode}", "red")
            except Exception as e:
                self.log(f"Update error: {e}", "red")
            finally:
                on_finish()

        threading.Thread(target=_update_task, daemon=True).start()