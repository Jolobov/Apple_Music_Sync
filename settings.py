# settings.py
import json
from typing import Dict, Any

import utils


class SettingsManager:
    def __init__(self):
        """Initializes settings with default values."""
        self.base_dir = utils.get_base_dir()
        self.settings_file = self.base_dir / "settings.json"

        self.defaults: Dict[str, Any] = {
            "codec_label": "m4a (AAC - Original)",
            "download_path": "",
            "cookies_path": "",
            "theme": "light"
        }

    def load(self) -> Dict[str, Any]:
        """
        Loads settings from JSON, merging them with defaults to ensure integrity.

        Returns:
            A dictionary containing application settings.
        """
        if not self.settings_file.exists():
            return self.defaults.copy()

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return self.defaults.copy()

            return self.defaults | data

        except (json.JSONDecodeError, OSError) as e:
            print(f"[Settings] Load error: {e}")
            return self.defaults.copy()

    def save(self, data: Dict[str, Any]) -> None:
        """
        Saves the settings dictionary to the JSON file.

        Args:
            data: Dictionary of settings to save.
        """
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except OSError as e:
            print(f"[Settings] Save error: {e}")

    def reset(self) -> None:
        """Resets the settings file to default values."""
        self.save(self.defaults)