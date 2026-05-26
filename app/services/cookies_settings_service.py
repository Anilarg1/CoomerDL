import json
import os


SIMPCITY_COOKIE_DOMAIN = "simpcity.cr"


class CookiesSettingsService:
    def __init__(self, cookies_path):
        self.cookies_path = str(cookies_path)

    def ensure_parent_dir(self):
        os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)

    def load_cookies_text(self) -> str:
        if not os.path.exists(self.cookies_path):
            return ""

        try:
            with open(self.cookies_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return json.dumps(data, indent=4, ensure_ascii=False)
                if isinstance(data, list):
                    return json.dumps(data, indent=4, ensure_ascii=False)
                return ""
        except Exception:
            try:
                with open(self.cookies_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return ""

    def parse_cookies_text(self, cookies_text: str):
        cookies_text = cookies_text.strip()
        if not cookies_text:
            return None

        return json.loads(cookies_text)

    def save_cookies_text(self, cookies_text: str):
        cookies_data = self.parse_cookies_text(cookies_text)
        self.ensure_parent_dir()

        with open(self.cookies_path, "w", encoding="utf-8") as f:
            json.dump(cookies_data, f, indent=4, ensure_ascii=False)

        return cookies_data

    def clear_cookies(self):
        self.ensure_parent_dir()
        with open(self.cookies_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)

    def import_cookies_file(self, source_path: str) -> str:
        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()

        # validar antes de devolver
        self.parse_cookies_text(content)
        return content

    def import_simpcity_cookies_from_browser(self, loader=None, browser_loaders=None):
        if browser_loaders is None:
            if loader is not None:
                browser_loaders = [loader]
            else:
                browser_loaders = self._get_browser_cookie_loaders()

        cookies = self._load_first_simpcity_cookie_set(browser_loaders)

        if not cookies:
            raise ValueError("No SimpCity cookies were found in the selected browser profile.")

        self.ensure_parent_dir()
        with open(self.cookies_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=4, ensure_ascii=False)

        return cookies

    def _get_browser_cookie_loaders(self):
        try:
            import browser_cookie3
        except ImportError as exc:
            raise RuntimeError(
                "browser-cookie3 is required to import SimpCity cookies from your browser."
            ) from exc

        loader_names = (
            "chrome",
            "edge",
            "firefox",
            "brave",
            "chromium",
            "vivaldi",
            "opera",
            "opera_gx",
        )
        return [
            getattr(browser_cookie3, name)
            for name in loader_names
            if callable(getattr(browser_cookie3, name, None))
        ]

    def _load_first_simpcity_cookie_set(self, browser_loaders):
        errors = []

        for browser_loader in browser_loaders:
            try:
                cookies = self._filter_simpcity_cookies(browser_loader(domain_name=SIMPCITY_COOKIE_DOMAIN))
                if cookies:
                    return cookies
                loader_name = getattr(browser_loader, "__name__", browser_loader.__class__.__name__)
                errors.append(f"{loader_name}: no SimpCity cookies")
            except Exception as exc:
                loader_name = getattr(browser_loader, "__name__", browser_loader.__class__.__name__)
                errors.append(f"{loader_name}: {type(exc).__name__}: {exc}")

        details = "; ".join(errors) if errors else "No browser loaders were available."
        raise ValueError(f"No SimpCity cookies were found in supported browser profiles. {details}")

    def _filter_simpcity_cookies(self, cookie_jar):
        cookies = []

        for cookie in cookie_jar:
            domain = str(getattr(cookie, "domain", "") or "").lower()
            if not self._is_simpcity_cookie_domain(domain):
                continue

            cookies.append(
                {
                    "name": getattr(cookie, "name", ""),
                    "value": getattr(cookie, "value", ""),
                    "domain": getattr(cookie, "domain", ""),
                    "path": getattr(cookie, "path", "/") or "/",
                    "secure": bool(getattr(cookie, "secure", False)),
                    "expires": getattr(cookie, "expires", None),
                }
            )

        return cookies

    def _is_simpcity_cookie_domain(self, domain: str) -> bool:
        normalized = domain.lstrip(".").lower()
        return normalized == SIMPCITY_COOKIE_DOMAIN or normalized.endswith(f".{SIMPCITY_COOKIE_DOMAIN}")
