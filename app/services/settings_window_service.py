import json
import os


class SettingsWindowService:
    DEFAULT_SETTINGS = {
        "max_downloads": 3,
        "folder_structure": "default",
        "max_retries": 3,
        "retry_interval": 2.0,
        "file_naming_mode": 0,
    }

    def __init__(self, config_path, on_settings_changed=None):
        self.config_path = config_path
        self.on_settings_changed = on_settings_changed

    def load_settings(self):
        if not os.path.exists(self.config_path):
            return dict(self.DEFAULT_SETTINGS)

        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                if not isinstance(data, dict):
                    return dict(self.DEFAULT_SETTINGS)

                merged = dict(self.DEFAULT_SETTINGS)
                merged.update(data)
                return merged
        except (FileNotFoundError, json.JSONDecodeError):
            return dict(self.DEFAULT_SETTINGS)

    def save_settings(self, settings: dict):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(settings, file, indent=4, ensure_ascii=False)

        if callable(self.on_settings_changed):
            self.on_settings_changed(settings)

    def center_window(self, window, width, height):
        try:
            screen = window.screen()
            if screen is not None:
                geometry = screen.availableGeometry()
                x = geometry.x() + (geometry.width() - width) // 2
                y = geometry.y() + (geometry.height() - height) // 2
                window.resize(width, height)
                window.move(x, y)
                return
        except Exception:
            pass
