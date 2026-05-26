import base64
import os
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


class Jpg5Adapter:
    site_name = "jpg5"
    decryption_key = b"seltilovessimpcity@simpcityhatesscrapers"

    def __init__(self, session, headers=None, log_callback=None, tr=None):
        self.session = session
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0",
        }
        self.log_callback = log_callback
        self.tr = tr if tr else (lambda x, **kwargs: x.format(**kwargs) if kwargs else x)

    def log(self, message, **kwargs):
        if kwargs:
            message = self.tr(message, **kwargs)
        else:
            message = self.tr(message)

        if self.log_callback:
            self.log_callback(self.site_name, message)

    def can_handle(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(name in host for name in ("jpg5", "jpg6", "jpg7", "cuckcapital", "selti-delivery"))

    def resolve_url(self, url):
        parsed = urlparse(url)
        if self._is_direct_cdn_file(url):
            entry = self._media_from_direct_url(url)
            return {"folder_name": self._build_folder_name(url), "media": [entry]}
        if parsed.path.startswith("/img/"):
            entry = self._resolve_media_page(url)
            return {"folder_name": self._build_folder_name(url), "media": [entry] if entry else []}
        return self.resolve_gallery(url)

    def _request_soup(self, url):
        response = self.session.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    def resolve_gallery(self, url):
        self.log("JPG5_PROCESSING_GALLERY", url=url)
        soup = self._request_soup(url)

        divs = soup.find_all("div", class_="list-item c8 gutter-margin-right-bottom")
        media = []

        for div in divs:
            enlaces = div.find_all("a", class_="image-container --media")
            for enlace in enlaces:
                href = enlace.get("href")
                if not href:
                    continue

                media_page_url = urljoin(url, href)

                try:
                    file_entry = self._resolve_media_page(media_page_url)
                    if file_entry:
                        media.append(file_entry)
                except Exception as e:
                    self.log("JPG5_ERROR_PROCESSING_MEDIA_PAGE", url=media_page_url, error=e)

        folder_name = self._build_folder_name(url)
        return {
            "folder_name": folder_name,
            "media": media,
        }

    def _is_direct_cdn_file(self, url):
        parsed = urlparse(url)
        extension = os.path.splitext(parsed.path)[1].lower()
        return extension in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm", ".mov"}

    def _fix_cdn_url(self, url):
        parsed = urlparse(url)
        host = parsed.netloc
        if "jpg5.su" in host:
            server = host.rsplit(".", 2)[0]
            return parsed._replace(netloc=f"{server}.cuckcapital.cr").geturl()
        return url

    def _decode_url(self, url):
        if url.startswith(("https:", "http:", "/")):
            return url
        encrypted_url = bytes.fromhex(base64.b64decode(url).decode())
        decoded = bytes(
            byte ^ self.decryption_key[index % len(self.decryption_key)]
            for index, byte in enumerate(encrypted_url)
        )
        return decoded.decode()

    def _full_size_url(self, url):
        parsed = urlparse(self._fix_cdn_url(url))
        path = re.sub(r"\.(md|th)(?=\.[^.]+$)", "", parsed.path)
        return parsed._replace(path=path, query="").geturl()

    def _media_from_direct_url(self, url):
        media_url = self._full_size_url(url)
        filename = os.path.basename(urlparse(media_url).path) or "jpg5_file"
        return {
            "media_url": media_url,
            "post_id": None,
            "title": "jpg5",
            "published": "",
            "folder_name": self._build_folder_name(url),
            "filename": filename,
        }

    def _resolve_media_page(self, media_page_url):
        self.log("JPG5_RESOLVING_MEDIA_PAGE", url=media_page_url)
        media_soup = self._request_soup(media_page_url)

        header_content = media_soup.find("div", class_="header-content-right")
        if not header_content:
            self.log("JPG5_HEADER_NOT_FOUND", url=media_page_url)
            return None

        btn_descarga = header_content.find("a", class_="btn btn-download default")
        if not btn_descarga or "href" not in btn_descarga.attrs:
            self.log("JPG5_FINAL_DOWNLOAD_LINK_NOT_FOUND", url=media_page_url)
            return None

        decoded_href = self._decode_url(btn_descarga["href"])
        descarga_url = self._full_size_url(urljoin(media_page_url, decoded_href))
        filename = os.path.basename(urlparse(descarga_url).path) or "jpg5_file"

        return {
            "media_url": descarga_url,
            "post_id": None,
            "title": "jpg5_gallery",
            "published": "",
            "folder_name": self._build_folder_name(media_page_url),
            "filename": filename,
        }

    def _build_folder_name(self, url):
        path = urlparse(url).path.strip("/").replace("/", "_")
        return path or "jpg5_gallery"
