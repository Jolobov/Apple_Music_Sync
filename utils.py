# utils.py
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def get_base_dir() -> Path:
    """
    Returns the absolute path to the application's base directory.
    Handles frozen executable state.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.resolve()


def get_tool_path(name: str, base_dir: Path) -> str:
    """
    Searches for an executable tool in PATH or local directory.

    Returns:
        Absolute path to the tool if found, otherwise the tool name.
    """
    if shutil.which(name):
        return name

    local_name = name
    if sys.platform == "win32" and not local_name.lower().endswith(".exe"):
        local_name += ".exe"

    local_tool = base_dir / local_name

    if local_tool.exists():
        return str(local_tool.resolve())

    return name


def open_path_in_os(path: Union[str, Path]) -> None:
    """
    Opens a file or directory using the default OS application.

    Raises:
        FileNotFoundError: If path does not exist.
        OSError: If opening the path fails.
    """
    target = Path(path)

    if not target.exists():
        raise FileNotFoundError(f"File not found: {target}")

    target_str = str(target)

    try:
        match sys.platform:
            case "win32":
                os.startfile(target_str)
            case "darwin":
                subprocess.Popen(["open", target_str])
            case "linux":
                subprocess.Popen(["xdg-open", target_str])
    except Exception as e:
        raise OSError(f"Failed to open {target_str}: {e}")


def clean_ansi(text: str) -> str:
    """Removes ANSI escape sequences from text."""
    if not text:
        return ""
    return ANSI_ESCAPE.sub('', text)


def get_startup_info() -> Optional[subprocess.STARTUPINFO]:
    """
    Returns Windows-specific startup flags to hide console window.

    Returns:
        STARTUPINFO for Windows, None for others.
    """
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


def get_subprocess_env() -> dict:
    """
    Returns environment variables optimized for subprocess execution
    (unbuffered output, no colors).
    """
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["NO_COLOR"] = "1"
    return env
