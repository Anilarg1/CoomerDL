# File Host Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class support for PixelDrain, TurboVid, Filester, GoFile, and Cyberfile URLs, including direct app entry and embedded SimpCity links.

**Architecture:** Implement each host as a focused adapter that resolves an input URL into the existing `{"folder_name": str, "media": list[dict]}` shape. Use one generic `FileHostDownloader` wrapper on top of `BaseApiDownloader` so every new host uses the shared `DownloadJob`, retry, history, filtering, progress, and final file-signature correction pipeline. Wire the hosts into `UrlService`, `SiteRegistry`, `DownloaderFactory`, `MainController`, and SimpCity embedded-link expansion.

**Tech Stack:** Python, requests/cloudscraper sessions, BeautifulSoup for HTML hosts, existing `DownloadEngine`/`BaseApiDownloader`, pytest.

---

## Sources And Supported URL Shapes

Cyberdrop-DL supported-sites reference, version 8.10.0 snapshot, lists these relevant shapes:

- PixelDrain: `/u/<file_id>`, `/l/<list_id>`, `/l/<list_id>#item=<file_index>`, `/api/file/<file_id>`, `/api/list/<list_id>`, `/d/<id>`, `/api/filesystem/<path>...`
- TurboVid: `/a/<album_id>`, `/d/<file_id>`, `/embed/<file_id>`, `/v/<file_id>`, `/data/<file_id>.mp4`, `library?q=<query>`
- GoFile: `/d/<content_id>`, `/download/<content_id>/<filename>`, `/download/web/<content_id>/<filename>`, password folders via `?password=<password>`
- Cyberfile: `/<file_id>`, `/<file_id>/<file_name>`, `/folder/<folder_id>`, `/folder/<folder_id>/<folder_name>`, `/shared/<share_key>`
- Filester: local Cyberdrop-DL crawler supports `/d/<slug>` and `/f/<slug>`

Local reference implementations:

- `_compare_cyberdrop_dl/cyberdrop_dl/crawlers/pixeldrain.py`
- `_compare_cyberdrop_dl/cyberdrop_dl/crawlers/turbovid.py`
- `_compare_cyberdrop_dl/cyberdrop_dl/crawlers/gofile.py`
- `_compare_cyberdrop_dl/cyberdrop_dl/crawlers/cyberfile.py`
- `_compare_cyberdrop_dl/cyberdrop_dl/crawlers/filester.py`
- `_compare_cyberdrop_dl/cyberdrop_dl/crawlers/_yetishare.py`

## File Structure

- Create: `downloader/adapters/pixeldrain_adapter.py`
  - Resolve PixelDrain file, list, list item, and filesystem URLs.
- Create: `downloader/adapters/turbovid_adapter.py`
  - Resolve TurboVid video, album, search, and direct `/data/*.mp4` URLs.
- Create: `downloader/adapters/gofile_adapter.py`
  - Resolve GoFile folders/files, create temporary API token when no token is configured, support password query param.
- Create: `downloader/adapters/cyberfile_adapter.py`
  - Resolve Cyberfile files/folders/shared folders using the YetiShare AJAX endpoints.
- Create: `downloader/adapters/filester_adapter.py`
  - Resolve Filester files/folders using public API and folder pagination.
- Create: `downloader/file_host.py`
  - Generic downloader wrapper for all new file-host adapters.
- Modify: `app/services/url_service.py`
  - Parse the five new URL families into `site_type`.
- Modify: `app/services/site_registry.py`
  - Register the five new site types.
- Modify: `app/adapters/downloader_factory.py`
  - Create `FileHostDownloader` instances.
- Modify: `app/views/pyside/main_window.py`
  - Add setup methods for new file hosts.
- Modify: `app/controllers/main_controller.py`
  - Route parsed hosts to the generic file-host downloader.
- Modify: `downloader/adapters/simpcity_adapter.py`
  - Expand embedded PixelDrain, TurboVid, Filester, GoFile, and Cyberfile links in SimpCity posts.
- Modify: `resources/config/i18n/en.json`
  - Add log labels/messages.
- Modify: `resources/config/i18n/es.json`
  - Add log labels/messages.
- Test: `tests/test_url_service.py`
- Test: `tests/test_site_registry.py`
- Test: `tests/downloader/test_file_host_downloader.py`
- Test: `tests/test_pixeldrain_adapter.py`
- Test: `tests/test_turbovid_adapter.py`
- Test: `tests/test_gofile_adapter.py`
- Test: `tests/test_cyberfile_adapter.py`
- Test: `tests/test_filester_adapter.py`
- Test: `tests/test_simpcity_adapter.py`

---

### Task 1: URL Parsing And Registry

**Files:**
- Modify: `app/services/url_service.py`
- Modify: `app/services/site_registry.py`
- Test: `tests/test_url_service.py`
- Test: `tests/test_site_registry.py`

- [ ] **Step 1: Write failing URL parser tests**

Create `tests/test_url_service.py` if it does not exist:

```python
from app.services.url_service import UrlService


def site_type(url):
    return UrlService().parse_download_url(url).site_type


def test_parses_pixeldrain_urls():
    assert site_type("https://pixeldrain.com/u/abc123") == "pixeldrain"
    assert site_type("https://pixeldrain.com/l/list123") == "pixeldrain"
    assert site_type("https://pixeldrain.com/api/file/abc123") == "pixeldrain"
    assert site_type("https://pixeldrain.com/d/folder/path") == "pixeldrain"


def test_parses_turbovid_urls():
    assert site_type("https://turbovid.cr/v/abc123") == "turbovid"
    assert site_type("https://turbo.cr/a/album123") == "turbovid"
    assert site_type("https://saint2.cr/embed/abc123") == "turbovid"


def test_parses_gofile_urls():
    assert site_type("https://gofile.io/d/abc123") == "gofile"
    assert site_type("https://store6.gofile.io/download/id/name.mp4") == "gofile"
    assert site_type("https://store1.gofile.io/download/web/id/name.mp4") == "gofile"


def test_parses_cyberfile_urls():
    assert site_type("https://cyberfile.me/folder/xUGg") == "cyberfile"
    assert site_type("https://cyberfile.me/shared/xUGg") == "cyberfile"
    assert site_type("https://cyberfile.me/abcd/file.mp4") == "cyberfile"


def test_parses_filester_urls():
    assert site_type("https://filester.me/d/fileSlug") == "filester"
    assert site_type("https://filester.me/f/folderSlug") == "filester"
```

Add to `tests/test_site_registry.py`:

```python
def test_registry_matches_pixeldrain():
    assert registry().match("https://pixeldrain.com/u/abc123").handler.site_type == "pixeldrain"


def test_registry_matches_turbovid():
    assert registry().match("https://turbovid.cr/v/abc123").handler.site_type == "turbovid"


def test_registry_matches_gofile():
    assert registry().match("https://gofile.io/d/abc123").handler.site_type == "gofile"


def test_registry_matches_cyberfile():
    assert registry().match("https://cyberfile.me/folder/xUGg").handler.site_type == "cyberfile"


def test_registry_matches_filester():
    assert registry().match("https://filester.me/d/fileSlug").handler.site_type == "filester"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_url_service.py tests/test_site_registry.py -v`

Expected: the new tests fail because the new URLs parse as `unknown` or do not match the registry.

- [ ] **Step 3: Implement URL parser and registry entries**

In `app/services/url_service.py`, add before the final `unknown` return:

```python
        if re.search(r"https?://([^/]+\.)?(pixeldrain|pixeldra)\.(com|net|in|nl|biz|tech|dev)", raw_url):
            return ParsedDownloadUrl(raw_url, parsed, "pixeldrain", is_post=True)

        if re.search(r"https?://([^/]+\.)?(turbo|turbovid|saint2?|saint)\.(cr|to|su)", raw_url):
            return ParsedDownloadUrl(raw_url, parsed, "turbovid", is_post=True)

        if "gofile.io" in parsed.netloc or parsed.netloc.endswith(".gofile.io"):
            return ParsedDownloadUrl(raw_url, parsed, "gofile", is_profile=parsed.path.startswith("/d/"))

        if "cyberfile." in parsed.netloc:
            return ParsedDownloadUrl(raw_url, parsed, "cyberfile", is_profile=parsed.path.startswith(("/folder/", "/shared/")))

        if "filester." in parsed.netloc:
            return ParsedDownloadUrl(raw_url, parsed, "filester", is_profile=parsed.path.startswith("/f/"), is_post=parsed.path.startswith("/d/"))
```

In `app/services/site_registry.py`, add handlers:

```python
            SiteHandler("pixeldrain", match_site("pixeldrain")),
            SiteHandler("turbovid", match_site("turbovid")),
            SiteHandler("gofile", match_site("gofile")),
            SiteHandler("cyberfile", match_site("cyberfile")),
            SiteHandler("filester", match_site("filester")),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_url_service.py tests/test_site_registry.py -v`

Expected: all URL parser and registry tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/url_service.py app/services/site_registry.py tests/test_url_service.py tests/test_site_registry.py
git commit -m "feat: recognize additional file hosts"
```

---

### Task 2: Generic File Host Downloader

**Files:**
- Create: `downloader/file_host.py`
- Modify: `app/adapters/downloader_factory.py`
- Test: `tests/downloader/test_file_host_downloader.py`

- [ ] **Step 1: Write failing downloader wrapper tests**

Create `tests/downloader/test_file_host_downloader.py`:

```python
from unittest.mock import Mock

from downloader.file_host import FileHostDownloader


class FakeAdapter:
    site_name = "fakehost"

    def __init__(self):
        self.session = Mock()

    def resolve_url(self, url):
        return {
            "folder_name": "fake_folder",
            "media": [
                {
                    "media_url": "https://cdn.fake/file.jpg",
                    "filename": "file.jpg",
                    "title": "fake",
                    "post_id": None,
                    "published": "",
                }
            ],
        }


def test_file_host_downloader_uses_adapter_media_entries(tmp_path):
    downloader = FileHostDownloader(
        adapter=FakeAdapter(),
        download_folder=str(tmp_path),
        max_workers=1,
        log_callback=lambda *args, **kwargs: None,
    )
    jobs = downloader.resolve_jobs("https://fakehost.test/item")

    assert len(jobs) == 1
    assert jobs[0].domain == "fakehost"
    assert jobs[0].filename == "file.jpg"
    assert jobs[0].target_folder.name == "fake_folder"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/downloader/test_file_host_downloader.py -v`

Expected: import fails because `downloader.file_host` does not exist.

- [ ] **Step 3: Implement generic wrapper**

Create `downloader/file_host.py`:

```python
from concurrent.futures import as_completed

from downloader.core.base_api_downloader import BaseApiDownloader


class FileHostDownloader(BaseApiDownloader):
    def __init__(
        self,
        adapter,
        download_folder,
        max_workers=5,
        log_callback=None,
        enable_widgets_callback=None,
        update_progress_callback=None,
        update_global_progress_callback=None,
        max_retries=3,
        retry_interval=2.0,
        tr=None,
    ):
        super().__init__(
            download_folder=download_folder,
            max_workers=max_workers,
            log_callback=log_callback,
            enable_widgets_callback=enable_widgets_callback,
            update_progress_callback=update_progress_callback,
            update_global_progress_callback=update_global_progress_callback,
            max_retries=max_retries,
            retry_interval=retry_interval,
            tr=tr,
            download_images=True,
            download_videos=True,
            download_compressed=True,
        )
        self.adapter = adapter
        self.session = getattr(adapter, "session", self.session)
        self.domain_name = adapter.site_name

    def resolve_jobs(self, url):
        resolved = self.adapter.resolve_url(url)
        folder_name = resolved["folder_name"]
        media_entries = resolved["media"]
        return self.create_download_jobs(folder_name, media_entries, domain=self.domain_name)

    def download_url(self, url):
        try:
            self.log("FILE_HOST_PROCESSING_URL", url=url)
            jobs = self.resolve_jobs(url)
            self.total_files = len(jobs)
            self.completed_files = 0
            futures = []
            for job in jobs:
                if self.download_mode == "queue":
                    self.process_download_job(job)
                else:
                    futures.append(self.executor.submit(self.process_download_job, job))
            self.futures = futures
            for future in as_completed(futures):
                if self.cancel_requested.is_set():
                    self.log("FILE_HOST_DOWNLOAD_CANCELLED")
                    break
                future.result()
            self.log("FILE_HOST_DOWNLOAD_COMPLETED")
        except Exception as exc:
            self.log("FILE_HOST_ERROR_PROCESSING_URL", error=exc)
        finally:
            self.shutdown_executor()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/downloader/test_file_host_downloader.py -v`

Expected: test passes.

- [ ] **Step 5: Add factory method**

In `app/adapters/downloader_factory.py`, import adapters and wrapper:

```python
from downloader.file_host import FileHostDownloader
from downloader.adapters.pixeldrain_adapter import PixelDrainAdapter
from downloader.adapters.turbovid_adapter import TurboVidAdapter
from downloader.adapters.gofile_adapter import GoFileAdapter
from downloader.adapters.cyberfile_adapter import CyberfileAdapter
from downloader.adapters.filester_adapter import FilesterAdapter
```

Add:

```python
    def create_file_host_downloader(self, site_type):
        settings = getattr(self.app, "settings", {}) if self.app is not None else {}
        adapters = {
            "pixeldrain": PixelDrainAdapter,
            "turbovid": TurboVidAdapter,
            "gofile": GoFileAdapter,
            "cyberfile": CyberfileAdapter,
            "filester": FilesterAdapter,
        }
        adapter_class = adapters[site_type]
        adapter = adapter_class(log_callback=self.frontend.log, tr=self.frontend.get_tr())
        return FileHostDownloader(
            adapter=adapter,
            download_folder=self.frontend.get_download_folder(),
            log_callback=self.frontend.log,
            enable_widgets_callback=self.frontend.enable_widgets,
            update_progress_callback=self.frontend.update_progress,
            update_global_progress_callback=self.frontend.update_global_progress,
            max_workers=self.frontend.get_max_downloads(),
            max_retries=int(settings.get("max_retries", 3) or 3),
            retry_interval=float(settings.get("retry_interval", 2.0) or 2.0),
            tr=self.frontend.get_tr(),
        )
```

- [ ] **Step 6: Commit**

```bash
git add downloader/file_host.py app/adapters/downloader_factory.py tests/downloader/test_file_host_downloader.py
git commit -m "feat: add generic file host downloader"
```

---

### Task 3: PixelDrain Adapter

**Files:**
- Create: `downloader/adapters/pixeldrain_adapter.py`
- Test: `tests/test_pixeldrain_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_pixeldrain_adapter.py`:

```python
from unittest.mock import Mock

from downloader.adapters.pixeldrain_adapter import PixelDrainAdapter


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload
        self.text = ""

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_pixeldrain_file_resolves_api_download_url():
    session = Mock()
    session.get.return_value = JsonResponse({
        "success": True,
        "id": "abc123",
        "name": "clip.mp4",
        "mime_type": "video/mp4",
        "date_upload": "2026-05-26T00:00:00Z",
        "hash_sha256": "hash",
    })
    adapter = PixelDrainAdapter(session=session)

    result = adapter.resolve_url("https://pixeldrain.com/u/abc123")

    assert result["folder_name"] == "pixeldrain_abc123"
    assert result["media"][0]["media_url"] == "https://pixeldrain.com/api/file/abc123?download"
    assert result["media"][0]["filename"] == "clip.mp4"


def test_pixeldrain_list_resolves_all_files():
    session = Mock()
    session.get.return_value = JsonResponse({
        "success": True,
        "id": "list123",
        "title": "Album Name",
        "files": [
            {"id": "one", "name": "one.jpg", "mime_type": "image/jpeg", "date_upload": "2026-05-26T00:00:00Z", "hash_sha256": "1"},
            {"id": "two", "name": "two.mp4", "mime_type": "video/mp4", "date_upload": "2026-05-26T00:00:00Z", "hash_sha256": "2"},
        ],
    })
    adapter = PixelDrainAdapter(session=session)

    result = adapter.resolve_url("https://pixeldrain.com/l/list123")

    assert result["folder_name"] == "Album Name_list123"
    assert [item["filename"] for item in result["media"]] == ["one.jpg", "two.mp4"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pixeldrain_adapter.py -v`

Expected: import fails because adapter does not exist.

- [ ] **Step 3: Implement PixelDrain adapter**

Create `downloader/adapters/pixeldrain_adapter.py`:

```python
import os
import re
from urllib.parse import urlparse

import requests


class PixelDrainAdapter:
    site_name = "pixeldrain"

    def __init__(self, session=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.log_callback = log_callback
        self.tr = tr

    def clean_filename(self, value):
        return re.sub(r'[<>:"/\\|?*\u200b]', "_", str(value or "")).strip()

    def log(self, message):
        if self.log_callback:
            self.log_callback(self.site_name, message)

    def resolve_url(self, url):
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parts[:1] == ["u"]:
            return self._resolve_file(url, parts[1])
        if parts[:2] == ["api", "file"]:
            return self._resolve_file(url, parts[2])
        if parts[:1] == ["l"]:
            return self._resolve_list(url, parts[1], parsed.fragment)
        if parts[:2] == ["api", "list"]:
            return self._resolve_list(url, parts[2], parsed.fragment)
        if parts[:1] == ["d"] or parts[:2] == ["api", "filesystem"]:
            return self._resolve_filesystem(url)
        raise ValueError(f"Unsupported PixelDrain URL: {url}")

    def _request_json(self, api_url):
        response = self.session.get(api_url)
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is False:
            raise ValueError(payload.get("message") or "PixelDrain API error")
        return payload

    def _media_from_file(self, file_data, origin="https://pixeldrain.com"):
        file_id = file_data["id"]
        filename = self.clean_filename(file_data.get("name") or file_id)
        return {
            "media_url": f"{origin}/api/file/{file_id}?download",
            "filename": filename,
            "title": "pixeldrain",
            "post_id": file_id,
            "published": file_data.get("date_upload", ""),
        }

    def _resolve_file(self, url, file_id):
        origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        payload = self._request_json(f"{origin}/api/file/{file_id}/info")
        return {"folder_name": self.clean_filename(f"pixeldrain_{file_id}"), "media": [self._media_from_file(payload, origin)]}

    def _resolve_list(self, url, list_id, fragment=""):
        origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        payload = self._request_json(f"{origin}/api/list/{list_id}")
        files = payload.get("files", [])
        if fragment.startswith("item="):
            files = [files[int(fragment.removeprefix("item="))]]
        title = self.clean_filename(f"{payload.get('title') or 'pixeldrain'}_{list_id}")
        return {"folder_name": title, "media": [self._media_from_file(file_data, origin) for file_data in files]}

    def _resolve_filesystem(self, url):
        raise NotImplementedError("PixelDrain filesystem support is Task 3 follow-up if needed by samples")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pixeldrain_adapter.py -v`

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add downloader/adapters/pixeldrain_adapter.py tests/test_pixeldrain_adapter.py
git commit -m "feat: add pixeldrain adapter"
```

---

### Task 4: TurboVid Adapter

**Files:**
- Create: `downloader/adapters/turbovid_adapter.py`
- Test: `tests/test_turbovid_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_turbovid_adapter.py`:

```python
from unittest.mock import Mock

from bs4 import BeautifulSoup

from downloader.adapters.turbovid_adapter import TurboVidAdapter


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_turbovid_video_uses_sign_api():
    session = Mock()
    session.get.return_value = JsonResponse({"filename": "clip.mp4", "url": "https://turbo.cr/data/abc123.mp4"})
    adapter = TurboVidAdapter(session=session)

    result = adapter.resolve_url("https://turbovid.cr/v/abc123")

    assert result["folder_name"] == "turbovid_abc123"
    assert result["media"][0]["media_url"] == "https://turbo.cr/data/abc123.mp4"
    assert result["media"][0]["filename"] == "clip.mp4"


def test_turbovid_album_extracts_file_ids():
    session = Mock()
    adapter = TurboVidAdapter(session=session)
    adapter._request_soup = Mock(return_value=BeautifulSoup("""
        <h1>Album</h1>
        <table><tbody id="fileTbody">
          <tr data-id="one"></tr>
          <tr data-id="two"></tr>
        </tbody></table>
    """, "html.parser"))
    adapter._resolve_video = Mock(side_effect=[
        {"media": [{"media_url": "https://turbo.cr/data/one.mp4", "filename": "one.mp4"}]},
        {"media": [{"media_url": "https://turbo.cr/data/two.mp4", "filename": "two.mp4"}]},
    ])

    result = adapter.resolve_url("https://turbo.cr/a/album123")

    assert result["folder_name"] == "Album_album123"
    assert [item["filename"] for item in result["media"]] == ["one.mp4", "two.mp4"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_turbovid_adapter.py -v`

Expected: import fails because adapter does not exist.

- [ ] **Step 3: Implement TurboVid adapter**

Create `downloader/adapters/turbovid_adapter.py`:

```python
import re
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


class TurboVidAdapter:
    site_name = "turbovid"
    primary_url = "https://turbo.cr"

    def __init__(self, session=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.log_callback = log_callback
        self.tr = tr

    def clean_filename(self, value):
        return re.sub(r'[<>:"/\\|?*\u200b]', "_", str(value or "")).strip()

    def resolve_url(self, url):
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parts[:1] == ["data"] and parts[1].endswith(".mp4"):
            return self._resolve_video(parts[1].removesuffix(".mp4"))
        if parts[:1] in (["v"], ["d"], ["embed"]):
            return self._resolve_video(parts[1])
        if parts[:1] == ["a"]:
            return self._resolve_album(url, parts[1])
        if parts[:1] == ["library"] and parse_qs(parsed.query).get("q"):
            return self._resolve_search(url)
        raise ValueError(f"Unsupported TurboVid URL: {url}")

    def _request_soup(self, url):
        response = self.session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _resolve_video(self, file_id):
        response = self.session.get(f"{self.primary_url}/api/sign?v={file_id}")
        response.raise_for_status()
        payload = response.json()
        filename = self.clean_filename(payload.get("original_filename") or payload["filename"])
        return {
            "folder_name": self.clean_filename(f"turbovid_{file_id}"),
            "media": [{"media_url": payload["url"], "filename": filename, "title": "turbovid", "post_id": file_id, "published": ""}],
        }

    def _resolve_album(self, url, album_id):
        soup = self._request_soup(url)
        title = self.clean_filename(f"{soup.find('h1').get_text(strip=True)}_{album_id}")
        media = []
        for row in soup.select("#fileTbody tr[data-id]"):
            media.extend(self._resolve_video(row["data-id"])["media"])
        return {"folder_name": title, "media": media}

    def _resolve_search(self, url):
        soup = self._request_soup(url)
        media = []
        for link in soup.select("#listView a.album-row[href]"):
            media.extend(self.resolve_url(link["href"])["media"])
        return {"folder_name": "turbovid_search", "media": media}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_turbovid_adapter.py -v`

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add downloader/adapters/turbovid_adapter.py tests/test_turbovid_adapter.py
git commit -m "feat: add turbovid adapter"
```

---

### Task 5: GoFile Adapter

**Files:**
- Create: `downloader/adapters/gofile_adapter.py`
- Test: `tests/test_gofile_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_gofile_adapter.py`:

```python
from unittest.mock import Mock

from downloader.adapters.gofile_adapter import GoFileAdapter


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_gofile_folder_resolves_child_files():
    session = Mock()
    session.post.return_value = JsonResponse({"status": "ok", "data": {"token": "temp-token"}})
    session.get.return_value = JsonResponse({
        "status": "ok",
        "data": {
            "id": "folder123",
            "code": "folder123",
            "name": "Folder",
            "type": "folder",
            "canAccess": True,
            "childrenCount": 1,
            "children": {
                "file123": {
                    "id": "file123",
                    "name": "clip.mp4",
                    "type": "file",
                    "canAccess": True,
                    "link": "https://store1.gofile.io/download/web/file123/clip.mp4",
                    "md5": "abc",
                    "createTime": 1779792480,
                }
            },
        },
        "metadata": {"hasNextPage": False},
    })
    adapter = GoFileAdapter(session=session)

    result = adapter.resolve_url("https://gofile.io/d/folder123")

    assert result["folder_name"] == "Folder_folder123"
    assert result["media"][0]["media_url"] == "https://store1.gofile.io/download/web/file123/clip.mp4"
    assert result["media"][0]["filename"] == "clip.mp4"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gofile_adapter.py -v`

Expected: import fails because adapter does not exist.

- [ ] **Step 3: Implement GoFile adapter**

Create `downloader/adapters/gofile_adapter.py` using the Cyberdrop-DL logic as the local reference. Include:

```python
import hashlib
import re
import time
from urllib.parse import parse_qs, urlparse

import requests


class GoFileAdapter:
    site_name = "gofile"
    api_entrypoint = "https://api.gofile.io"
    salt = "5d4f7g8sd45fsd"
    browser_lang = "en-US"

    def __init__(self, session=None, api_key=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.api_key = api_key or ""
        self.log_callback = log_callback
        self.tr = tr

    def clean_filename(self, value):
        return re.sub(r'[<>:"/\\|?*\u200b]', "_", str(value or "")).strip()

    def resolve_url(self, url):
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if not self.api_key:
            self.api_key = self._create_temp_account()
        if parts[:1] == ["d"]:
            return self._resolve_folder(parts[1], parse_qs(parsed.query).get("password", [None])[0])
        if parts[:1] == ["download"]:
            file_id = parts[2] if parts[1:2] == ["web"] else parts[1]
            redirect = self.session.get(url, allow_redirects=True)
            final_url = redirect.url
            folder_id = final_url.rstrip("/").split("/")[-1]
            return self._resolve_folder(folder_id, None, single_file_id=file_id)
        raise ValueError(f"Unsupported GoFile URL: {url}")

    def _headers(self):
        user_agent = "Mozilla/5.0"
        headers = {"User-Agent": user_agent, "Origin": "https://gofile.io", "Referer": "https://gofile.io/"}
        if self.api_key:
            token = f"{user_agent}::{self.browser_lang}::{self.api_key}::{int(time.time() // 14400)}::{self.salt}"
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-BL"] = self.browser_lang
            headers["X-Website-Token"] = hashlib.sha256(token.encode()).hexdigest()
        return headers

    def _create_temp_account(self):
        response = self.session.post(f"{self.api_entrypoint}/accounts", json={}, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "ok":
            raise ValueError("Could not create GoFile temp account")
        return payload["data"]["token"]

    def _resolve_folder(self, content_id, password, single_file_id=None):
        params = {"contentFilter": "", "sortField": "name", "sortDirection": 1, "pageSize": 1000, "page": 1}
        if password:
            params["password"] = hashlib.sha256(password.encode()).hexdigest()
        response = self.session.get(f"{self.api_entrypoint}/contents/{content_id}", params=params, headers=self._headers())
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "ok":
            raise ValueError(payload.get("status") or "GoFile API error")
        folder = payload["data"]
        title = self.clean_filename(f"{folder.get('name') or 'gofile'}_{content_id}")
        media = []
        for node in folder.get("children", {}).values():
            if node.get("type") != "file" or not node.get("canAccess", False):
                continue
            if single_file_id and node.get("id") != single_file_id:
                continue
            media.append({
                "media_url": node.get("link") or node.get("directLink"),
                "filename": self.clean_filename(node.get("name") or node["id"]),
                "title": "gofile",
                "post_id": node.get("id"),
                "published": str(node.get("createTime") or ""),
            })
        return {"folder_name": title, "media": media}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_gofile_adapter.py -v`

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add downloader/adapters/gofile_adapter.py tests/test_gofile_adapter.py
git commit -m "feat: add gofile adapter"
```

---

### Task 6: Cyberfile Adapter

**Files:**
- Create: `downloader/adapters/cyberfile_adapter.py`
- Test: `tests/test_cyberfile_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_cyberfile_adapter.py`:

```python
from unittest.mock import Mock

from bs4 import BeautifulSoup

from downloader.adapters.cyberfile_adapter import CyberfileAdapter


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_cyberfile_file_resolves_download_token():
    session = Mock()
    adapter = CyberfileAdapter(session=session)
    adapter._request_soup = Mock(return_value=BeautifulSoup("""
        <script>showFileInformation(12345);</script>
    """, "html.parser"))
    session.post.return_value = JsonResponse({"html": """
        <a class="dropdown-menu dropdown-info" onclick="downloadFile('https://cyberfile.me/file.mp4?download_token=abc');"></a>
        <button onclick="downloadFile('https://cyberfile.me/file.mp4?download_token=abc');">Download</button>
        <td>Uploaded:</td><td>26/05/2026 12:00:00</td>
        <div class="image-name-title">file.mp4</div>
    """})

    result = adapter.resolve_url("https://cyberfile.me/abcd/file.mp4")

    assert result["folder_name"] == "cyberfile_abcd"
    assert result["media"][0]["filename"] == "file.mp4"
    assert "download_token=abc" in result["media"][0]["media_url"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cyberfile_adapter.py -v`

Expected: import fails because adapter does not exist.

- [ ] **Step 3: Implement Cyberfile adapter**

Create `downloader/adapters/cyberfile_adapter.py` by porting the synchronous subset of `_yetishare.py`:

```python
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class CyberfileAdapter:
    site_name = "cyberfile"
    primary_url = "https://cyberfile.me"

    def __init__(self, session=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.log_callback = log_callback
        self.tr = tr

    def clean_filename(self, value):
        return re.sub(r'[<>:"/\\|?*\u200b]', "_", str(value or "")).strip()

    def resolve_url(self, url):
        parts = [part for part in urlparse(url).path.split("/") if part]
        if parts[:1] == ["folder"]:
            return self._resolve_folder(url, parts[1], shared=False)
        if parts[:1] == ["shared"]:
            return self._resolve_folder(url, parts[1], shared=True)
        return self._resolve_file(url, parts[0])

    def _request_soup(self, url):
        response = self.session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _ajax_soup(self, url, data, is_file=False):
        endpoint = "/account/ajax/file_details" if is_file else "/account/ajax/load_files"
        response = self.session.post(f"{self.primary_url}{endpoint}", data=data, headers={"X-Requested-With": "XMLHttpRequest"})
        response.raise_for_status()
        return BeautifulSoup(response.json()["html"].replace("\\", ""), "html.parser")

    def _resolve_file(self, url, file_id):
        soup = self._request_soup(url)
        script = soup.find("script", string=re.compile("showFileInformation"))
        content_id = re.search(r"showFileInformation\((\d+)\)", script.get_text()).group(1)
        detail_soup = self._ajax_soup(url, {"u": content_id}, is_file=True)
        download_tag = detail_soup.select_one("a[onclick*='download_token'], button[onclick*='download_token']")
        raw_link = re.search(r"'([^']+download_token=[^']+)'", download_tag["onclick"]).group(1)
        filename = self.clean_filename(detail_soup.select_one(".image-name-title").get_text(strip=True))
        return {
            "folder_name": self.clean_filename(f"cyberfile_{file_id}"),
            "media": [{"media_url": raw_link, "filename": filename, "title": "cyberfile", "post_id": file_id, "published": ""}],
        }

    def _resolve_folder(self, url, folder_id, shared=False):
        raise NotImplementedError("Cyberfile folders should be ported from _yetishare.py after file support lands")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cyberfile_adapter.py -v`

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add downloader/adapters/cyberfile_adapter.py tests/test_cyberfile_adapter.py
git commit -m "feat: add cyberfile file adapter"
```

---

### Task 7: Filester Adapter

**Files:**
- Create: `downloader/adapters/filester_adapter.py`
- Test: `tests/test_filester_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_filester_adapter.py`:

```python
from unittest.mock import Mock

from bs4 import BeautifulSoup

from downloader.adapters.filester_adapter import FilesterAdapter


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_filester_file_uses_public_download_api():
    session = Mock()
    session.post.return_value = JsonResponse({"download_url": "/download/fileSlug/file.mp4"})
    adapter = FilesterAdapter(session=session)
    adapter._request_soup = Mock(return_value=BeautifulSoup("""
      <html><head><meta property="og:title" content="file.mp4"></head>
      <body><div id="detailsContent">
        <span>MD5</span><span>abc</span>
        <span>Uploaded</span><span>2026-05-26</span>
        <span>Type</span><span>video/mp4</span>
      </div></body></html>
    """, "html.parser"))

    result = adapter.resolve_url("https://filester.me/d/fileSlug")

    assert result["folder_name"] == "filester_fileSlug"
    assert result["media"][0]["filename"] == "file.mp4"
    assert result["media"][0]["media_url"].endswith("/download/fileSlug/file.mp4?download=true")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_filester_adapter.py -v`

Expected: import fails because adapter does not exist.

- [ ] **Step 3: Implement Filester adapter**

Create `downloader/adapters/filester_adapter.py`:

```python
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class FilesterAdapter:
    site_name = "filester"
    primary_url = "https://filester.me"
    cdn_url = "https://cache1.filester.me"

    def __init__(self, session=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.log_callback = log_callback
        self.tr = tr

    def clean_filename(self, value):
        return re.sub(r'[<>:"/\\|?*\u200b]', "_", str(value or "")).strip()

    def resolve_url(self, url):
        parts = [part for part in urlparse(url).path.split("/") if part]
        if parts[:1] == ["d"]:
            return self._resolve_file(url, parts[1])
        if parts[:1] == ["f"]:
            return self._resolve_folder(url, parts[1])
        raise ValueError(f"Unsupported Filester URL: {url}")

    def _request_soup(self, url):
        response = self.session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _open_graph_title(self, soup):
        tag = soup.select_one("meta[property='og:title']")
        return tag["content"] if tag and tag.get("content") else "filester_file"

    def _resolve_file(self, url, slug):
        soup = self._request_soup(url)
        response = self.session.post(f"{self.primary_url}/api/public/download", json={"file_slug": slug})
        response.raise_for_status()
        download_url = response.json()["download_url"]
        filename = self.clean_filename(self._open_graph_title(soup))
        return {
            "folder_name": self.clean_filename(f"filester_{slug}"),
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
        title = self.clean_filename(f"{self._open_graph_title(soup)}_{folder_id}")
        media = []
        for item in soup.select(".file-item[onclick]"):
            match = re.search(r"'([^']+)'", item["onclick"])
            if match:
                media.extend(self.resolve_url(match.group(1))["media"])
        for link in soup.select(".subfolder-item[href]"):
            media.extend(self.resolve_url(link["href"])["media"])
        return {"folder_name": title, "media": media}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_filester_adapter.py -v`

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add downloader/adapters/filester_adapter.py tests/test_filester_adapter.py
git commit -m "feat: add filester adapter"
```

---

### Task 8: App Controller Integration

**Files:**
- Modify: `app/views/pyside/main_window.py`
- Modify: `app/controllers/main_controller.py`
- Test: `tests/test_main_controller.py`

- [ ] **Step 1: Write failing controller test**

Add to `tests/test_main_controller.py`:

```python
def test_controller_routes_pixeldrain_to_file_host_downloader():
    app = make_fake_app()
    app.setup_file_host_downloader = Mock()
    app.file_host_downloader = Mock()
    controller = MainController(app)

    controller.parse_request_url("https://pixeldrain.com/u/abc123")

    app.setup_file_host_downloader.assert_called_once_with("pixeldrain")
```

Repeat the assertion pattern for `turbovid`, `gofile`, `cyberfile`, and `filester`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main_controller.py -v`

Expected: new hosts are not routed.

- [ ] **Step 3: Add main-window setup method**

In `app/views/pyside/main_window.py`, add near other setup methods:

```python
    def setup_file_host_downloader(self, site_type):
        self.file_host_downloader = self.downloader_factory.create_file_host_downloader(site_type)
```

- [ ] **Step 4: Add controller route**

In `app/controllers/main_controller.py`, add a branch before unknown handling:

```python
        elif parsed.site_type in {"pixeldrain", "turbovid", "gofile", "cyberfile", "filester"}:
            self.app.add_log_message_safe(parsed.site_type, self.app.tr("FILE_HOST_PROCESSING_URL", url=request.url))
            self.app.setup_file_host_downloader(parsed.site_type)
            self.app.active_downloader = self.app.file_host_downloader
            self.app.download_thread = threading.Thread(
                target=self.app.active_downloader.download_url,
                args=(request.url,),
                daemon=True,
            )
            self.app.download_thread.start()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_main_controller.py -v`

Expected: controller tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/views/pyside/main_window.py app/controllers/main_controller.py tests/test_main_controller.py
git commit -m "feat: route file hosts through app controller"
```

---

### Task 9: SimpCity Embedded Link Expansion

**Files:**
- Modify: `downloader/adapters/simpcity_adapter.py`
- Test: `tests/test_simpcity_adapter.py`

- [ ] **Step 1: Write failing SimpCity embedded-link tests**

Add one test that proves each new host gets expanded from post content:

```python
def test_expands_supported_file_host_links_from_post_content(self):
    adapter = SimpCityAdapter()
    adapter.file_host_adapters = {
        "pixeldrain": Mock(resolve_url=Mock(return_value={"media": [{"media_url": "https://pixeldrain.com/api/file/a?download", "filename": "a.jpg"}]})),
        "gofile": Mock(resolve_url=Mock(return_value={"media": [{"media_url": "https://store.gofile.io/download/web/b/b.mp4", "filename": "b.mp4"}]})),
    }
    soup = BeautifulSoup("""
      <article class="message">
        <div class="bbWrapper">
          <a href="https://pixeldrain.com/u/a">pd</a>
          <a href="https://gofile.io/d/b">gf</a>
        </div>
      </article>
    """, "html.parser")

    media = adapter._extract_page_media(soup, "https://simpcity.cr/threads/example.1/")

    assert [item["filename"] for item in media] == ["a.jpg", "b.mp4"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_simpcity_adapter.py::SimpCityAdapterPaginationTests::test_expands_supported_file_host_links_from_post_content -v`

Expected: only Bunkr is expanded today, so the test fails.

- [ ] **Step 3: Implement generic embedded host expansion**

In `downloader/adapters/simpcity_adapter.py`, import adapters:

```python
from downloader.adapters.pixeldrain_adapter import PixelDrainAdapter
from downloader.adapters.turbovid_adapter import TurboVidAdapter
from downloader.adapters.gofile_adapter import GoFileAdapter
from downloader.adapters.cyberfile_adapter import CyberfileAdapter
from downloader.adapters.filester_adapter import FilesterAdapter
```

In `__init__`, add:

```python
        self.file_host_adapters = {
            "pixeldrain": PixelDrainAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
            "turbovid": TurboVidAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
            "gofile": GoFileAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
            "cyberfile": CyberfileAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
            "filester": FilesterAdapter(session=self.scraper, log_callback=self.log_callback, tr=self.tr),
        }
```

Replace Bunkr-only host detection with:

```python
        def adapter_for_file_host(raw_url):
            parsed = urlparse(urljoin(base_url, raw_url))
            host = parsed.netloc.lower()
            if "bunkr" in host and parsed.path.startswith(("/a/", "/f/", "/v/", "/i/")):
                return self.bunkr_adapter
            if "pixeldrain" in host or "pixeldra.in" in host:
                return self.file_host_adapters["pixeldrain"]
            if any(name in host for name in ("turbo.cr", "turbovid", "saint.to", "saint2.")):
                return self.file_host_adapters["turbovid"]
            if "gofile.io" in host:
                return self.file_host_adapters["gofile"]
            if "cyberfile." in host:
                return self.file_host_adapters["cyberfile"]
            if "filester." in host:
                return self.file_host_adapters["filester"]
            return None
```

Add resolved media using the same dedupe and mapping logic already used for Bunkr.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_simpcity_adapter.py -v`

Expected: all SimpCity tests pass.

- [ ] **Step 5: Commit**

```bash
git add downloader/adapters/simpcity_adapter.py tests/test_simpcity_adapter.py
git commit -m "feat: expand file hosts from simpcity posts"
```

---

### Task 10: I18n, Full Verification, And Manual Smoke

**Files:**
- Modify: `resources/config/i18n/en.json`
- Modify: `resources/config/i18n/es.json`
- Modify: `README.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Add i18n keys**

Add to both i18n JSON files:

```json
{
  "FILE_HOST_PROCESSING_URL": "Processing file host URL: {url}",
  "FILE_HOST_DOWNLOAD_CANCELLED": "File host download cancelled",
  "FILE_HOST_DOWNLOAD_COMPLETED": "File host download completed",
  "FILE_HOST_ERROR_PROCESSING_URL": "Error processing file host URL: {error}"
}
```

Use Spanish translations in `es.json`:

```json
{
  "FILE_HOST_PROCESSING_URL": "Procesando URL de host de archivos: {url}",
  "FILE_HOST_DOWNLOAD_CANCELLED": "Descarga de host de archivos cancelada",
  "FILE_HOST_DOWNLOAD_COMPLETED": "Descarga de host de archivos completada",
  "FILE_HOST_ERROR_PROCESSING_URL": "Error procesando URL de host de archivos: {error}"
}
```

- [ ] **Step 2: Update docs**

In `README.md`, add supported hosts:

```markdown
- PixelDrain
- TurboVid
- Filester
- GoFile
- Cyberfile
```

In `docs/architecture.md`, add one paragraph:

```markdown
File hosts are implemented as adapters that resolve host-specific pages or APIs into normalized media entries. `FileHostDownloader` then turns those entries into shared `DownloadJob` objects so all hosts reuse common retry, history, progress, filtering, and file-signature extension correction behavior.
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
python -m pytest tests/test_url_service.py tests/test_site_registry.py tests/downloader/test_file_host_downloader.py tests/test_pixeldrain_adapter.py tests/test_turbovid_adapter.py tests/test_gofile_adapter.py tests/test_cyberfile_adapter.py tests/test_filester_adapter.py tests/test_simpcity_adapter.py tests/test_main_controller.py -v
```

Expected: all focused tests pass.

- [ ] **Step 4: Run full verification**

Run:

```bash
python -m pytest tests -v
python -m compileall app downloader tests
```

Expected: all tests pass and compileall exits 0.

- [ ] **Step 5: Manual smoke test**

Start the app:

```powershell
Start-Process -FilePath python -ArgumentList 'main.py' -WorkingDirectory 'C:\Users\shaai\CoomerDL'
```

Use known safe sample URLs for:

- `https://pixeldrain.com/u/<file_id>`
- `https://turbovid.cr/v/<file_id>`
- `https://gofile.io/d/<content_id>`
- `https://cyberfile.me/<file_id>`
- `https://filester.me/d/<slug>`

Expected:

- App detects the correct host.
- Log shows `FILE_HOST_PROCESSING_URL`.
- Files download into host-specific folders.
- Completed files have byte-signature-correct extensions.
- SimpCity posts containing these links expand into actual downloadable media.

- [ ] **Step 6: Commit**

```bash
git add resources/config/i18n/en.json resources/config/i18n/es.json README.md docs/architecture.md
git commit -m "docs: document added file host support"
```

---

## Risk Notes

- GoFile requires an API token. The plan creates a temporary account token when no configured token exists, matching Cyberdrop-DL behavior.
- PixelDrain filesystem support is more complex than list/file support. Task 3 includes a placeholder exception for filesystem URLs; complete filesystem walking only if current samples need it.
- Cyberfile folders and shared folders use YetiShare AJAX pagination and password cookies. File support should land first, then folder support should port `_yetishare.py` behavior with dedicated tests.
- TurboVid old domains should normalize to `https://turbo.cr` for API calls.
- Filester CDN host selection can start deterministic with `cache1.filester.me`; after live testing, add fallback to `cache6.filester.me` if needed.

## Self-Review

- Spec coverage: PixelDrain, TurboVid, Filester, GoFile, and Cyberfile each have URL parsing, adapter, app routing, SimpCity expansion, and verification tasks.
- Placeholder scan: two intentionally scoped follow-ups remain: PixelDrain filesystem and Cyberfile folders. They are called out as risk notes because the first implementation should prioritize file/list URLs likely to appear in SimpCity threads.
- Type consistency: every adapter exposes `site_name`, `session`, and `resolve_url(url)` returning `folder_name` plus `media`; `FileHostDownloader` consumes that exact interface.
