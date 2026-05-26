import json
import os


class TranslationService:
    def __init__(self, language="en", locales_dir="resources/config/i18n"):
        self.locales_dir = locales_dir
        self.language = "en"
        self.default_language = "en"
        self.translations = {}
        self.default_translations = {}
        self.load_translations()

    def _load_json_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def load_translations(self, language=None):
        self.language = "en"
        default_path = os.path.join(self.locales_dir, f"{self.default_language}.json")
        self.default_translations = self._load_json_file(default_path)
        self.translations = dict(self.default_translations)

    def set_language(self, language):
        self.load_translations()

    def tr(self, key, **kwargs):
        text = self.translations.get(key, self.default_translations.get(key, key))

        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def get_available_languages(self):
        return [{"code": "en", "name": "English"}]
