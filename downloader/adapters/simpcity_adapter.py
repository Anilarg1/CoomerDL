import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from downloader.adapters.bunkr_adapter import BunkrAdapter
from downloader.adapters.filester_adapter import FilesterAdapter
from downloader.adapters.gofile_adapter import GoFileAdapter
from downloader.adapters.jpg5_adapter import Jpg5Adapter
from downloader.adapters.pixeldrain_adapter import PixelDrainAdapter
from downloader.adapters.turbovid_adapter import TurboVidAdapter


class SimpCityAdapter:
    site_name = "simpcity"

    def __init__(
        self,
        cookies_path="resources/config/cookies/simpcity.json",
        log_callback=None,
        tr=None,
        page_max_retries=3,
        page_retry_interval=2.0,
    ):
        self.cookies_path = cookies_path
        self.log_callback = log_callback
        self.tr = tr if tr else (lambda x, **kwargs: x.format(**kwargs) if kwargs else x)
        self.page_max_retries = max(int(page_max_retries or 0), 0)
        self.page_retry_interval = max(float(page_retry_interval or 0), 0.0)

        try:
            import cloudscraper
        except ImportError as e:
            raise ImportError(
                "SimpCity requires the 'cloudscraper' package. "
                "Install it with: pip install cloudscraper"
            ) from e

        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.bunkr_adapter = BunkrAdapter(
            session=self.scraper,
            log_callback=self.log_callback,
            tr=self.tr,
        )
        self.file_host_adapters = {
            "pixeldrain": PixelDrainAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
            "turbovid": TurboVidAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
            "gofile": GoFileAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
            "filester": FilesterAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
            "jpg5": Jpg5Adapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
        }

        self.title_selector = "h1[class=p-title-value]"
        self.posts_selector = "div[class*=message-main]"
        self.post_content_selector = "div[class*=message-userContent]"
        self.images_selector = "img[class*=bbImage]"
        self.videos_selector = "video source, video[src]"
        self.attachments_block_selector = "section[class=message-attachments]"
        self.attachments_selector = "a"
        self.next_page_selector = "a[class*=pageNav-jump--next]"

        self.set_cookies()

    def log(self, message, **kwargs):
        if kwargs:
            message = self.tr(message, **kwargs)
        else:
            message = self.tr(message)

        if self.log_callback:
            self.log_callback(self.site_name, message)

    def sanitize_folder_name(self, name):
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def set_cookies(self):
        if not os.path.exists(self.cookies_path):
            return

        with open(self.cookies_path, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        if isinstance(cookies, dict):
            cookies = [cookies]

        for c in cookies:
            if isinstance(c, dict) and "name" in c and "value" in c:
                self.scraper.cookies.set(c["name"], c["value"])

    def can_handle(self, url: str):
        host = urlparse(url).netloc.lower()
        return "simpcity" in host

    def fetch_page(self, url):
        response = self.scraper.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    def _fetch_page_with_retries(self, url):
        last_error = None
        total = self.page_max_retries + 1

        for attempt in range(total):
            try:
                return self.fetch_page(url)
            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt < self.page_max_retries:
                    self.log(
                        "SIMPCITY_PAGE_FETCH_RETRY",
                        url=url,
                        retry_interval=self.page_retry_interval,
                        attempt=attempt + 1,
                        total=total,
                    )
                    if self.page_retry_interval > 0:
                        time.sleep(self.page_retry_interval)

        raise last_error

    def resolve_thread(self, url, paginate=True, download_images=True, download_videos=True, download_attachments=True):
        self.log("SIMPCITY_PROCESSING_THREAD", url=url)

        all_media = []
        visited = set()
        current_url = url
        folder_name = None

        while current_url and current_url not in visited:
            visited.add(current_url)

            try:
                soup = self._fetch_page_with_retries(current_url)
            except requests.exceptions.RequestException:
                if not all_media and folder_name is None:
                    self.log("SIMPCITY_PAGE_FAILED_NO_RESULTS", url=current_url)
                    raise

                self.log("SIMPCITY_PAGE_FAILED_USING_PARTIAL_RESULTS", url=current_url)
                break

            if folder_name is None:
                title_element = soup.select_one(self.title_selector)
                folder_name = (
                    self.sanitize_folder_name(title_element.text.strip())
                    if title_element
                    else self.tr("SIMPCITY_DEFAULT_FOLDER")
                )

            page_media = self._extract_page_media(
                soup,
                base_url=current_url,
                folder_name=folder_name,
                download_images=download_images,
                download_videos=download_videos,
                download_attachments=download_attachments,
            )
            all_media.extend(page_media)

            if not paginate:
                break

            next_page = soup.select_one(self.next_page_selector)
            if next_page and next_page.get("href"):
                current_url = urljoin(current_url, next_page.get("href"))
            else:
                current_url = None

        return {
            "folder_name": folder_name or self.tr("SIMPCITY_DEFAULT_FOLDER"),
            "media": all_media,
        }

    def _extract_page_media(self, soup, base_url, folder_name, download_images=True, download_videos=True, download_attachments=True):
        media = []
        seen = set()
        resolved_host_links = set()
        video_extensions = (".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".wmv", ".flv")

        def adapter_for_file_host(raw_url, include_image_hosts=True):
            if not raw_url:
                return None
            parsed = urlparse(urljoin(base_url, raw_url))
            host = parsed.netloc.lower()
            if "bunkr" in host and parsed.path.startswith(("/a/", "/f/", "/v/", "/i/")):
                return self.bunkr_adapter
            if "pixeldrain" in host or "pixeldra.in" in host:
                return self.file_host_adapters.get("pixeldrain")
            if any(name in host for name in ("turbo.cr", "turbovid", "saint.to", "saint2.")):
                return self.file_host_adapters.get("turbovid")
            if "gofile.io" in host:
                return self.file_host_adapters.get("gofile")
            if "filester." in host:
                return self.file_host_adapters.get("filester")
            if any(name in host for name in ("jpg5", "jpg6", "jpg7", "cuckcapital", "selti-delivery")):
                if not include_image_hosts:
                    return None
                return self.file_host_adapters.get("jpg5")
            return None

        def add_media(raw_url, fallback_filename):
            if not raw_url:
                return
            media_url = urljoin(base_url, raw_url)
            if media_url in seen:
                return
            seen.add(media_url)

            media.append({
                "media_url": media_url,
                "post_id": None,
                "title": folder_name,
                "published": "",
                "folder_name": folder_name,
                "filename": os.path.basename(urlparse(media_url).path) or fallback_filename,
            })

        def add_resolved_host_media(raw_url):
            host_url = urljoin(base_url, raw_url)
            if host_url in resolved_host_links:
                return
            adapter = adapter_for_file_host(host_url)
            if adapter is None:
                return
            resolved_host_links.add(host_url)

            try:
                resolved = adapter.resolve_url(host_url)
            except Exception as exc:
                self.log("SIMPCITY_FILE_HOST_LINK_FAILED", url=host_url, error=exc)
                return

            for entry in resolved.get("media", []):
                media_url = entry.get("media_url")
                if not media_url or media_url in seen:
                    continue
                seen.add(media_url)
                media.append({
                    "media_url": media_url,
                    "post_id": entry.get("post_id"),
                    "title": entry.get("title") or resolved.get("folder_name") or folder_name,
                    "published": entry.get("published", ""),
                    "folder_name": resolved.get("folder_name") or folder_name,
                    "filename": entry.get("filename") or os.path.basename(urlparse(media_url).path) or "filehost",
                })

        message_inners = soup.select(self.posts_selector)
        for post in message_inners:
            post_content = post.select_one(self.post_content_selector)
            if not post_content:
                continue

            if download_images:
                for img in post_content.select(self.images_selector):
                    src = img.get("src")
                    add_media(src, "image")

            if download_videos:
                for video in post_content.select(self.videos_selector):
                    src = video.get("src")
                    add_media(src, "video")

                for link in post_content.select("a[href]"):
                    href = link.get("href")
                    if adapter_for_file_host(href, include_image_hosts=download_images):
                        add_resolved_host_media(href)
                        continue
                    extension = os.path.splitext(urlparse(href or "").path)[1].lower()
                    if extension in video_extensions:
                        add_media(href, "video")

                for embedded in post_content.select("iframe[src], embed[src]"):
                    src = embedded.get("src")
                    if adapter_for_file_host(src, include_image_hosts=download_images):
                        add_resolved_host_media(src)

            if download_attachments:
                attachments_block = post_content.select_one(self.attachments_block_selector)
                if attachments_block:
                    for attachment in attachments_block.select(self.attachments_selector):
                        href = attachment.get("href")
                        if adapter_for_file_host(href, include_image_hosts=download_images):
                            add_resolved_host_media(href)
                            continue
                        add_media(href, "attachment")

        return media
