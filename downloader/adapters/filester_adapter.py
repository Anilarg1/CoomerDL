from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from downloader.adapters.file_host_utils import clean_filename


class FilesterAdapter:
    site_name = "filester"
    primary_url = "https://filester.me"
    cdn_url = "https://cache1.filester.me"

    def __init__(self, session=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.log_callback = log_callback
        self.tr = tr

    def resolve_url(self, url):
        parts = [part for part in urlparse(url).path.split("/") if part]
        if parts[:1] == ["d"] and len(parts) >= 2:
            return self._resolve_file(url, parts[1])
        if parts[:1] == ["f"] and len(parts) >= 2:
            return self._resolve_folder(url, parts[1])
        raise ValueError(f"Unsupported Filester URL: {url}")

    def _request_soup(self, url):
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text or response.content, "html.parser")

    def _open_graph_title(self, soup):
        tag = soup.select_one("meta[property='og:title']")
        return tag["content"] if tag and tag.get("content") else "filester_file"

    def _resolve_file(self, url, slug):
        soup = self._request_soup(url)
        response = self.session.post(f"{self.primary_url}/api/public/download", json={"file_slug": slug}, timeout=20)
        response.raise_for_status()
        download_url = response.json()["download_url"]
        filename = clean_filename(self._open_graph_title(soup))
        return {
            "folder_name": clean_filename(f"filester_{slug}"),
            "media": [{
                "media_url": urljoin(self.cdn_url, download_url) + "?download=true",
                "filename": filename,
                "title": "filester",
                "post_id": slug,
                "published": "",
            }],
        }

    def _resolve_folder(self, url, folder_id):
        soup = self._request_soup(url)
        title = clean_filename(f"{self._open_graph_title(soup)}_{folder_id}")
        media = []
        for item in soup.select(".file-item[onclick]"):
            onclick = item["onclick"]
            if "'" in onclick:
                media.extend(self.resolve_url(onclick.split("'", 2)[1])["media"])
        for link in soup.select(".subfolder-item[href]"):
            media.extend(self.resolve_url(urljoin(url, link["href"]))["media"])
        return {"folder_name": title, "media": media}
