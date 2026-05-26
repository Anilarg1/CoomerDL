import time
from hashlib import sha256
from urllib.parse import parse_qs, urlparse

import requests

from downloader.adapters.file_host_utils import clean_filename


class GoFileAdapter:
    site_name = "gofile"
    api_url = "https://api.gofile.io"
    salt = "g4f8fd9f12h14g"
    browser_lang = "en-US"

    def __init__(self, session=None, api_token=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.api_token = api_token
        self.log_callback = log_callback
        self.tr = tr

    def resolve_url(self, url):
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parts[:1] == ["d"] and len(parts) >= 2:
            password = (parse_qs(parsed.query).get("password") or [None])[0]
            return self._resolve_folder(parts[1], password=password)
        if parts[:1] == ["download"] and len(parts) >= 3:
            return self._resolve_direct(url, parts[-1])
        raise ValueError(f"Unsupported GoFile URL: {url}")

    def _headers(self):
        if not self.api_token:
            self.api_token = self._create_temp_account()
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        return {
            "User-Agent": user_agent,
            "Authorization": f"Bearer {self.api_token}",
            "Origin": "https://gofile.io",
            "Referer": "https://gofile.io/",
            "X-BL": self.browser_lang,
            "X-Website-Token": self._create_web_token(user_agent),
        }

    def _create_web_token(self, user_agent):
        token = f"{user_agent}::{self.browser_lang}::{self.api_token}::{int(time.time() // 14400)}::{self.salt}"
        return sha256(token.encode()).hexdigest()

    def _create_temp_account(self):
        response = self.session.post(f"{self.api_url}/accounts", json={}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "ok":
            raise ValueError("Could not create GoFile temporary API token")
        return payload["data"]["token"]

    def _resolve_folder(self, content_id, password=None):
        params = {"contentFilter": "", "sortField": "name", "sortDirection": 1, "pageSize": 1000, "page": 1}
        if password:
            params["password"] = sha256(password.encode(), usedforsecurity=False).hexdigest()
        response = self.session.get(f"{self.api_url}/contents/{content_id}", params=params, headers=self._headers(), timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "ok":
            raise ValueError(f"GoFile API error: {payload.get('status')}")
        root = payload["data"]
        media = []
        self._collect_files(root, media)
        return {"folder_name": clean_filename(f"{root.get('name') or 'gofile'}_{content_id}"), "media": media}

    def _collect_files(self, node, media):
        if node.get("canAccess") is False:
            return
        if node.get("type") == "file":
            link = node.get("link") or node.get("directLink")
            if link:
                media.append({
                    "media_url": link,
                    "filename": clean_filename(node.get("name") or node.get("id") or "gofile_file"),
                    "title": "gofile",
                    "post_id": node.get("id"),
                    "published": str(node.get("createTime") or ""),
                    "checksum": node.get("md5", ""),
                })
            return
        for child in (node.get("children") or {}).values():
            self._collect_files(child, media)

    def _resolve_direct(self, url, filename):
        return {
            "folder_name": "gofile_file",
            "media": [{"media_url": url, "filename": clean_filename(filename), "title": "gofile", "post_id": None, "published": ""}],
        }
