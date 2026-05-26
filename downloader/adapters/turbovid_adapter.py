from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from downloader.adapters.file_host_utils import clean_filename


class TurboVidAdapter:
    site_name = "turbovid"
    primary_url = "https://turbo.cr"

    def __init__(self, session=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.log_callback = log_callback
        self.tr = tr

    def resolve_url(self, url):
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parts[:1] in (["v"], ["d"], ["embed"]) and len(parts) >= 2:
            return self._resolve_video(parts[1])
        if parts[:1] == ["data"] and parts[-1].endswith(".mp4"):
            return self._resolve_direct(url)
        if parts[:1] == ["a"] and len(parts) >= 2:
            return self._resolve_album(url, parts[1])
        if parsed.path.strip("/") == "library":
            return self._resolve_search(url)
        raise ValueError(f"Unsupported TurboVid URL: {url}")

    def _request_json(self, url):
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.json()

    def _request_soup(self, url):
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text or response.content, "html.parser")

    def _resolve_video(self, file_id):
        payload = self._request_json(f"{self.primary_url}/api/sign?v={file_id}")
        filename = clean_filename(payload.get("original_filename") or payload.get("filename") or f"{file_id}.mp4")
        return {
            "folder_name": clean_filename(f"turbovid_{file_id}"),
            "media": [{
                "media_url": payload["url"],
                "filename": filename,
                "title": "turbovid",
                "post_id": file_id,
                "published": "",
                "mime_type": "video/mp4",
            }],
        }

    def _resolve_direct(self, url):
        filename = clean_filename(urlparse(url).path.rsplit("/", 1)[-1] or "turbovid.mp4")
        file_id = filename.removesuffix(".mp4")
        return {
            "folder_name": clean_filename(f"turbovid_{file_id}"),
            "media": [{"media_url": url, "filename": filename, "title": "turbovid", "post_id": file_id, "published": "", "mime_type": "video/mp4"}],
        }

    def _resolve_album(self, url, album_id):
        soup = self._request_soup(url)
        title = clean_filename(f"{(soup.select_one('h1').get_text(strip=True) if soup.select_one('h1') else 'turbovid')}_{album_id}")
        media = []
        for row in soup.select("#fileTbody tr[data-id], tr[data-id]"):
            media.extend(self._resolve_video(row["data-id"])["media"])
        return {"folder_name": title, "media": media}

    def _resolve_search(self, url):
        soup = self._request_soup(url)
        media = []
        for link in soup.select("#listView a.album-row[href], a.album-row[href]"):
            media.extend(self.resolve_url(link["href"])["media"])
        return {"folder_name": "turbovid_search", "media": media}
