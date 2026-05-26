# Downloader Architecture Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize CoomerDL's downloader architecture by borrowing the best ideas from Cyberdrop-DL and KToolBox: URL registry dispatch, normalized download jobs, a shared download engine, and a cleaner Coomer/Kemono flow.

**Architecture:** Keep the PySide UI and existing site behavior intact while introducing new seams behind it. First route site selection through a registry, then make site adapters produce normalized `DownloadJob` objects, then centralize file transfer/retry/history/progress into a shared engine, and finally migrate each site one at a time.

**Tech Stack:** Python, PySide6, `requests`/threading for the first migration phase, SQLite, pytest, existing CoomerDL services/adapters. Async/httpx can be evaluated after the sync shared engine is stable.

---

## Scope And Strategy

This plan intentionally avoids a large async rewrite in the first pass. Cyberdrop-DL's async crawler framework is excellent, but copying that shape all at once would create too much risk for a desktop GUI app that already works. KToolBox's job-based Coomer/Kemono model is the safer bridge.

The modernization happens in four phases:

1. Add a site registry without changing downloader behavior.
2. Add a normalized `DownloadJob` model and a shared planning interface.
3. Extract a shared synchronous download engine from existing CoomerDL logic.
4. Migrate Coomer/Kemono first, then SimpCity, then Bunkr/Erome/JPG5/CoomerFans.

Each phase should leave the app runnable.

## File Structure

### New Files

- `app/models/site_handler.py`
  - Defines `SiteHandler` metadata and the interface used by `MainController`.

- `app/services/site_registry.py`
  - Owns URL matching and handler lookup.
  - Replaces hardcoded controller dispatch gradually.

- `tests/test_site_registry.py`
  - Covers URL routing for Coomer/Kemono, Bunkr, Erome, SimpCity, JPG5, CoomerFans, and unknown URLs.

- `downloader/models/download_job.py`
  - Defines normalized job data: URL, target folder, filename, post metadata, media type, headers, domain, and database key.

- `downloader/models/download_result.py`
  - Defines structured download outcomes: completed, skipped, failed, cancelled.

- `downloader/engine/download_engine.py`
  - Shared transfer implementation: temp files, resume, retry, DB cache checks, progress callback calls, cancellation.

- `downloader/engine/download_history.py`
  - SQLite history wrapper around `resources/config/downloads.db`.

- `downloader/engine/download_filters.py`
  - Shared extension and media-type filtering.

- `downloader/planners/coomer_kemono_planner.py`
  - Converts Coomer/Kemono API posts into `DownloadJob` instances.

- `tests/downloader/test_download_job.py`
  - Covers normalized job defaults and path/filename behavior.

- `tests/downloader/test_download_history.py`
  - Covers SQLite insert, lookup, skip, and clear behavior using a temp DB.

- `tests/downloader/test_download_filters.py`
  - Covers image/video/compressed/document/other filtering.

- `tests/downloader/test_download_engine.py`
  - Covers completed, skipped, retry, cancellation, and partial-file resume with mocked responses.

- `tests/downloader/test_coomer_kemono_planner.py`
  - Covers planner output from representative Coomer/Kemono post payloads.

### Existing Files To Modify

- `app/controllers/main_controller.py`
  - Replace the long URL dispatch chain with registry lookup in stages.

- `app/services/url_service.py`
  - Keep `ParsedDownloadUrl`, but allow registry handlers to own site matching over time.

- `app/adapters/downloader_factory.py`
  - Add factory methods for registry handlers and the shared engine.

- `downloader/downloader.py`
  - Migrate Coomer/Kemono to planner plus shared engine.
  - Leave legacy methods during transition until tests prove parity.

- `downloader/core/base_api_downloader.py`
  - Move reusable download code into `downloader/engine`.
  - Keep compatibility wrappers for existing site downloaders.

- `downloader/simpcity.py`
  - Later migration to return jobs from `SimpCityAdapter.resolve_thread()`.

- `downloader/bunkr.py`
  - Later migration to shared engine.

- `downloader/erome.py`
  - Later migration to shared engine.

- `downloader/jpg5.py`
  - Later migration to shared engine.

- `downloader/coomerfans.py`
  - Later migration to shared engine.

---

## Task 1: Add Site Registry Without Behavior Changes

**Files:**
- Create: `app/models/site_handler.py`
- Create: `app/services/site_registry.py`
- Modify: `app/services/url_service.py`
- Test: `tests/test_site_registry.py`

- [ ] **Step 1: Write failing registry tests**

Create `tests/test_site_registry.py`:

```python
from app.services.site_registry import SiteRegistry, build_default_site_registry


def test_registry_matches_coomer_profile():
    registry = build_default_site_registry()

    match = registry.match("https://coomer.st/onlyfans/user/abc123")

    assert match is not None
    assert match.handler.site_type == "coomer_kemono"
    assert match.parsed.service == "onlyfans"
    assert match.parsed.user == "abc123"
    assert match.parsed.post is None


def test_registry_matches_coomer_post():
    registry = build_default_site_registry()

    match = registry.match("https://coomer.st/onlyfans/user/abc123/post/999")

    assert match is not None
    assert match.handler.site_type == "coomer_kemono"
    assert match.parsed.service == "onlyfans"
    assert match.parsed.user == "abc123"
    assert match.parsed.post == "999"
    assert match.parsed.is_post is True


def test_registry_matches_kemono_search_offset():
    registry = build_default_site_registry()

    match = registry.match("https://kemono.cr/patreon/user/abc123?q=test&o=50")

    assert match is not None
    assert match.handler.site_type == "coomer_kemono"
    assert match.parsed.query == "test"
    assert match.parsed.offset == 50


def test_registry_matches_bunkr_album():
    registry = build_default_site_registry()

    match = registry.match("https://bunkr.cr/a/example")

    assert match is not None
    assert match.handler.site_type == "bunkr"
    assert match.parsed.is_profile is True
    assert match.parsed.is_post is False


def test_registry_matches_bunkr_file_post():
    registry = build_default_site_registry()

    match = registry.match("https://bunkr.cr/f/example")

    assert match is not None
    assert match.handler.site_type == "bunkr"
    assert match.parsed.is_post is True


def test_registry_matches_erome_album():
    registry = build_default_site_registry()

    match = registry.match("https://www.erome.com/a/album-id")

    assert match is not None
    assert match.handler.site_type == "erome"
    assert match.parsed.is_album is True


def test_registry_matches_simpcity():
    registry = build_default_site_registry()

    match = registry.match("https://simpcity.cr/threads/example.123/")

    assert match is not None
    assert match.handler.site_type == "simpcity"


def test_registry_matches_jpg5():
    registry = build_default_site_registry()

    match = registry.match("https://jpg5.su/album/example")

    assert match is not None
    assert match.handler.site_type == "jpg5"


def test_registry_matches_coomerfans_post():
    registry = build_default_site_registry()

    match = registry.match("https://coomerfans.com/p/example")

    assert match is not None
    assert match.handler.site_type == "coomerfans"
    assert match.parsed.is_post is True


def test_registry_returns_none_for_unknown_url():
    registry = build_default_site_registry()

    match = registry.match("https://example.com/nope")

    assert match is None
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_site_registry.py -v
```

Expected: FAIL because `app.services.site_registry` does not exist.

- [ ] **Step 3: Create site handler model**

Create `app/models/site_handler.py`:

```python
from dataclasses import dataclass
from typing import Callable

from app.services.url_service import ParsedDownloadUrl


UrlMatcher = Callable[[str], ParsedDownloadUrl | None]


@dataclass(frozen=True)
class SiteHandler:
    site_type: str
    matcher: UrlMatcher
```

- [ ] **Step 4: Create site registry**

Create `app/services/site_registry.py`:

```python
from dataclasses import dataclass

from app.models.site_handler import SiteHandler
from app.services.url_service import ParsedDownloadUrl, UrlService


@dataclass(frozen=True)
class SiteMatch:
    handler: SiteHandler
    parsed: ParsedDownloadUrl


class SiteRegistry:
    def __init__(self, handlers: list[SiteHandler]):
        self.handlers = handlers

    def match(self, raw_url: str) -> SiteMatch | None:
        for handler in self.handlers:
            parsed = handler.matcher(raw_url)
            if parsed is not None and parsed.site_type != "unknown":
                return SiteMatch(handler=handler, parsed=parsed)
        return None


def build_default_site_registry(url_service: UrlService | None = None) -> SiteRegistry:
    service = url_service or UrlService()

    def match_site(site_type: str):
        def matcher(raw_url: str) -> ParsedDownloadUrl | None:
            parsed = service.parse_download_url(raw_url)
            if parsed.site_type == site_type:
                return parsed
            return None

        return matcher

    return SiteRegistry(
        [
            SiteHandler("erome", match_site("erome")),
            SiteHandler("bunkr", match_site("bunkr")),
            SiteHandler("coomer_kemono", match_site("coomer_kemono")),
            SiteHandler("simpcity", match_site("simpcity")),
            SiteHandler("jpg5", match_site("jpg5")),
            SiteHandler("coomerfans", match_site("coomerfans")),
        ]
    )
```

- [ ] **Step 5: Run registry tests**

Run:

```bash
pytest tests/test_site_registry.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/models/site_handler.py app/services/site_registry.py tests/test_site_registry.py
git commit -m "feat: add site registry"
```

---

## Task 2: Route MainController Through Registry

**Files:**
- Modify: `app/controllers/main_controller.py`
- Test: `tests/test_main_controller.py`

- [ ] **Step 1: Add controller test for registry parsing**

Add this test to `tests/test_main_controller.py`:

```python
from app.controllers.main_controller import MainController
from app.services.site_registry import build_default_site_registry


def test_controller_uses_registry_for_url_parsing(fake_app):
    controller = MainController(fake_app)

    parsed = controller.parse_request_url("https://coomer.st/onlyfans/user/abc123")

    assert parsed.site_type == "coomer_kemono"
    assert parsed.service == "onlyfans"
    assert parsed.user == "abc123"
```

If the existing test file does not have `fake_app`, create a minimal fixture:

```python
import pytest


class FakeApp:
    def __init__(self):
        self.site_registry = build_default_site_registry()


@pytest.fixture
def fake_app():
    return FakeApp()
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_main_controller.py::test_controller_uses_registry_for_url_parsing -v
```

Expected: FAIL because `parse_request_url` does not exist.

- [ ] **Step 3: Add registry lookup method**

Modify `app/controllers/main_controller.py`:

```python
from app.services.site_registry import build_default_site_registry
```

Add this method inside `MainController`:

```python
    def parse_request_url(self, raw_url):
        registry = getattr(self.app, "site_registry", None)
        if registry is None:
            registry = build_default_site_registry(self.app.url_service)
            self.app.site_registry = registry

        match = registry.match(raw_url)
        if match is None:
            return self.app.url_service.parse_download_url(raw_url)
        return match.parsed
```

Then change this line in `start_download`:

```python
        parsed = self.app.url_service.parse_download_url(request.url)
```

to:

```python
        parsed = self.parse_request_url(request.url)
```

- [ ] **Step 4: Run controller tests**

Run:

```bash
pytest tests/test_main_controller.py -v
```

Expected: PASS.

- [ ] **Step 5: Run URL and registry tests**

Run:

```bash
pytest tests/test_site_registry.py tests/test_main_controller.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/controllers/main_controller.py tests/test_main_controller.py
git commit -m "refactor: route controller URL parsing through registry"
```

---

## Task 3: Add Normalized DownloadJob And DownloadResult Models

**Files:**
- Create: `downloader/models/download_job.py`
- Create: `downloader/models/download_result.py`
- Test: `tests/downloader/test_download_job.py`

- [ ] **Step 1: Write failing model tests**

Create `tests/downloader/test_download_job.py`:

```python
from pathlib import Path

from downloader.models.download_job import DownloadJob
from downloader.models.download_result import DownloadResult, DownloadStatus


def test_download_job_uses_url_as_default_database_key():
    job = DownloadJob(
        media_url="https://n1.kemono.cr/data/file.jpg",
        target_folder=Path("downloads"),
        filename="file.jpg",
        domain="kemono",
    )

    assert job.database_key == "https://n1.kemono.cr/data/file.jpg"


def test_download_job_final_path_is_target_folder_joined_to_filename():
    job = DownloadJob(
        media_url="https://n1.kemono.cr/data/file.jpg",
        target_folder=Path("downloads"),
        filename="file.jpg",
        domain="kemono",
    )

    assert job.final_path == Path("downloads") / "file.jpg"
    assert job.temp_path == Path("downloads") / "file.jpg.tmp"


def test_download_result_completed_constructor():
    result = DownloadResult.completed("https://example.com/file.jpg", Path("file.jpg"), 100)

    assert result.status == DownloadStatus.COMPLETED
    assert result.media_url == "https://example.com/file.jpg"
    assert result.file_size == 100
    assert result.message == "completed"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/downloader/test_download_job.py -v
```

Expected: FAIL because the model modules do not exist.

- [ ] **Step 3: Create DownloadJob**

Create `downloader/models/download_job.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DownloadJob:
    media_url: str
    target_folder: Path
    filename: str
    domain: str
    headers: dict[str, str] = field(default_factory=dict)
    user_id: str | None = None
    post_id: str | None = None
    post_name: str | None = None
    post_time: str | None = None
    media_type: str = "other"
    database_key: str | None = None

    def __post_init__(self):
        if self.database_key is None:
            object.__setattr__(self, "database_key", self.media_url)

    @property
    def final_path(self) -> Path:
        return self.target_folder / self.filename

    @property
    def temp_path(self) -> Path:
        return self.target_folder / f"{self.filename}.tmp"
```

- [ ] **Step 4: Create DownloadResult**

Create `downloader/models/download_result.py`:

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DownloadStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class DownloadResult:
    status: DownloadStatus
    media_url: str
    file_path: Path | None = None
    file_size: int = 0
    message: str = ""

    @classmethod
    def completed(cls, media_url: str, file_path: Path, file_size: int):
        return cls(
            status=DownloadStatus.COMPLETED,
            media_url=media_url,
            file_path=file_path,
            file_size=file_size,
            message="completed",
        )

    @classmethod
    def skipped(cls, media_url: str, message: str):
        return cls(status=DownloadStatus.SKIPPED, media_url=media_url, message=message)

    @classmethod
    def failed(cls, media_url: str, message: str):
        return cls(status=DownloadStatus.FAILED, media_url=media_url, message=message)

    @classmethod
    def cancelled(cls, media_url: str):
        return cls(status=DownloadStatus.CANCELLED, media_url=media_url, message="cancelled")
```

- [ ] **Step 5: Run model tests**

Run:

```bash
pytest tests/downloader/test_download_job.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add downloader/models/download_job.py downloader/models/download_result.py tests/downloader/test_download_job.py
git commit -m "feat: add normalized download job models"
```

---

## Task 4: Extract Download History

**Files:**
- Create: `downloader/engine/download_history.py`
- Test: `tests/downloader/test_download_history.py`

- [ ] **Step 1: Write failing history tests**

Create `tests/downloader/test_download_history.py`:

```python
from downloader.engine.download_history import DownloadHistory


def test_history_records_and_finds_download(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")

    history.record_completed(
        media_url="https://example.com/file.jpg",
        file_path=str(tmp_path / "file.jpg"),
        file_size=123,
        user_id="user",
        post_id="post",
    )

    assert history.contains("https://example.com/file.jpg") is True
    assert history.get("https://example.com/file.jpg") == (str(tmp_path / "file.jpg"), 123)


def test_history_returns_false_for_unknown_download(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")

    assert history.contains("https://example.com/missing.jpg") is False
    assert history.get("https://example.com/missing.jpg") is None


def test_history_clear_removes_all_downloads(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")
    history.record_completed("url", "path", 1)

    history.clear()

    assert history.contains("url") is False
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/downloader/test_download_history.py -v
```

Expected: FAIL because `DownloadHistory` does not exist.

- [ ] **Step 3: Implement DownloadHistory**

Create `downloader/engine/download_history.py`:

```python
import sqlite3
import threading
from pathlib import Path


class DownloadHistory:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.lock = threading.Lock()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_url TEXT UNIQUE,
                    file_path TEXT,
                    file_size INTEGER,
                    user_id TEXT,
                    post_id TEXT,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.connection.commit()

    def contains(self, media_url: str) -> bool:
        return self.get(media_url) is not None

    def get(self, media_url: str) -> tuple[str, int] | None:
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT file_path, file_size FROM downloads WHERE media_url = ?", (media_url,))
            row = cursor.fetchone()
        if row is None:
            return None
        return row[0], row[1]

    def record_completed(
        self,
        media_url: str,
        file_path: str,
        file_size: int,
        user_id: str | None = None,
        post_id: str | None = None,
    ):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO downloads (media_url, file_path, file_size, user_id, post_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (media_url, file_path, file_size, user_id, post_id),
            )
            self.connection.commit()

    def clear(self):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM downloads")
            self.connection.commit()
```

- [ ] **Step 4: Run history tests**

Run:

```bash
pytest tests/downloader/test_download_history.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add downloader/engine/download_history.py tests/downloader/test_download_history.py
git commit -m "feat: extract download history store"
```

---

## Task 5: Extract Download Filters

**Files:**
- Create: `downloader/engine/download_filters.py`
- Test: `tests/downloader/test_download_filters.py`

- [ ] **Step 1: Write failing filter tests**

Create `tests/downloader/test_download_filters.py`:

```python
from downloader.engine.download_filters import classify_extension, should_download_extension


def test_classify_extension():
    assert classify_extension(".jpg") == "image"
    assert classify_extension(".mp4") == "video"
    assert classify_extension(".zip") == "compressed"
    assert classify_extension(".pdf") == "document"
    assert classify_extension(".bin") == "other"


def test_should_download_respects_media_flags():
    assert should_download_extension(".jpg", download_images=True, download_videos=False, download_compressed=False)
    assert not should_download_extension(".mp4", download_images=True, download_videos=False, download_compressed=True)
    assert not should_download_extension(".zip", download_images=True, download_videos=True, download_compressed=False)
    assert should_download_extension(".pdf", download_images=False, download_videos=False, download_compressed=False)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/downloader/test_download_filters.py -v
```

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement filters**

Create `downloader/engine/download_filters.py`:

```python
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".wmv", ".m4v")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff")
DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx")
COMPRESSED_EXTENSIONS = (".zip", ".rar", ".7z", ".tar", ".gz")


def classify_extension(extension: str) -> str:
    ext = extension.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in COMPRESSED_EXTENSIONS:
        return "compressed"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    return "other"


def should_download_extension(
    extension: str,
    *,
    download_images: bool,
    download_videos: bool,
    download_compressed: bool,
) -> bool:
    media_type = classify_extension(extension)
    if media_type == "image":
        return download_images
    if media_type == "video":
        return download_videos
    if media_type == "compressed":
        return download_compressed
    return True
```

- [ ] **Step 4: Run filter tests**

Run:

```bash
pytest tests/downloader/test_download_filters.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add downloader/engine/download_filters.py tests/downloader/test_download_filters.py
git commit -m "feat: extract download filters"
```

---

## Task 6: Implement Shared Synchronous Download Engine

**Files:**
- Create: `downloader/engine/download_engine.py`
- Test: `tests/downloader/test_download_engine.py`

- [ ] **Step 1: Write failing engine tests**

Create `tests/downloader/test_download_engine.py`:

```python
import threading
from pathlib import Path

from downloader.engine.download_engine import DownloadEngine
from downloader.engine.download_history import DownloadHistory
from downloader.models.download_job import DownloadJob
from downloader.models.download_result import DownloadStatus


class FakeResponse:
    def __init__(self, chunks, status_code=200, headers=None):
        self.chunks = chunks
        self.status_code = status_code
        self.headers = headers or {"content-length": str(sum(len(chunk) for chunk in chunks))}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=1048576):
        yield from self.chunks


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, url, stream=True, headers=None, timeout=None):
        self.requests.append((url, headers or {}))
        return self.responses.pop(0)


def make_job(tmp_path):
    return DownloadJob(
        media_url="https://example.com/file.jpg",
        target_folder=tmp_path,
        filename="file.jpg",
        domain="example",
    )


def test_engine_downloads_file_and_records_history(tmp_path):
    session = FakeSession([FakeResponse([b"abc", b"def"])])
    history = DownloadHistory(tmp_path / "downloads.db")
    engine = DownloadEngine(session=session, history=history, cancel_event=threading.Event())

    result = engine.download(make_job(tmp_path))

    assert result.status == DownloadStatus.COMPLETED
    assert (tmp_path / "file.jpg").read_bytes() == b"abcdef"
    assert history.contains("https://example.com/file.jpg")


def test_engine_skips_existing_history(tmp_path):
    session = FakeSession([])
    history = DownloadHistory(tmp_path / "downloads.db")
    history.record_completed("https://example.com/file.jpg", str(tmp_path / "file.jpg"), 10)
    engine = DownloadEngine(session=session, history=history, cancel_event=threading.Event())

    result = engine.download(make_job(tmp_path))

    assert result.status == DownloadStatus.SKIPPED
    assert result.message == "already downloaded"


def test_engine_resumes_from_temp_file(tmp_path):
    temp_path = tmp_path / "file.jpg.tmp"
    temp_path.write_bytes(b"abc")
    session = FakeSession([FakeResponse([b"def"], status_code=206, headers={"content-length": "3"})])
    history = DownloadHistory(tmp_path / "downloads.db")
    engine = DownloadEngine(session=session, history=history, cancel_event=threading.Event())

    result = engine.download(make_job(tmp_path))

    assert result.status == DownloadStatus.COMPLETED
    assert (tmp_path / "file.jpg").read_bytes() == b"abcdef"
    assert session.requests[0][1]["Range"] == "bytes=3-"


def test_engine_cancels_before_download(tmp_path):
    cancel_event = threading.Event()
    cancel_event.set()
    session = FakeSession([])
    history = DownloadHistory(tmp_path / "downloads.db")
    engine = DownloadEngine(session=session, history=history, cancel_event=cancel_event)

    result = engine.download(make_job(tmp_path))

    assert result.status == DownloadStatus.CANCELLED
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/downloader/test_download_engine.py -v
```

Expected: FAIL because `DownloadEngine` does not exist.

- [ ] **Step 3: Implement DownloadEngine**

Create `downloader/engine/download_engine.py`:

```python
import os
import time
from pathlib import Path

from downloader.engine.download_history import DownloadHistory
from downloader.models.download_job import DownloadJob
from downloader.models.download_result import DownloadResult


class DownloadEngine:
    def __init__(
        self,
        *,
        session,
        history: DownloadHistory,
        cancel_event,
        max_retries: int = 3,
        retry_interval: float = 1.0,
        request_timeout=(10, 120),
        progress_callback=None,
        log_callback=None,
    ):
        self.session = session
        self.history = history
        self.cancel_event = cancel_event
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.request_timeout = request_timeout
        self.progress_callback = progress_callback
        self.log_callback = log_callback

    def log(self, domain: str, message: str):
        if self.log_callback:
            self.log_callback(domain, message)

    def download(self, job: DownloadJob) -> DownloadResult:
        if self.cancel_event.is_set():
            return DownloadResult.cancelled(job.media_url)

        if self.history.contains(job.database_key):
            return DownloadResult.skipped(job.media_url, "already downloaded")

        job.target_folder.mkdir(parents=True, exist_ok=True)

        for attempt in range(self.max_retries + 1):
            if self.cancel_event.is_set():
                self._remove_temp(job.temp_path)
                return DownloadResult.cancelled(job.media_url)

            try:
                return self._download_once(job)
            except Exception as exc:
                if attempt >= self.max_retries:
                    self._remove_temp(job.temp_path)
                    return DownloadResult.failed(job.media_url, str(exc))
                time.sleep(self.retry_interval)

        return DownloadResult.failed(job.media_url, "download failed")

    def _download_once(self, job: DownloadJob) -> DownloadResult:
        headers = dict(job.headers)
        downloaded_size = 0
        if job.temp_path.exists():
            downloaded_size = job.temp_path.stat().st_size
            if downloaded_size:
                headers["Range"] = f"bytes={downloaded_size}-"

        response = self.session.get(
            job.media_url,
            stream=True,
            headers=headers,
            timeout=self.request_timeout,
        )
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0) or 0)
        start_time = time.time()

        with open(job.temp_path, "ab") as file:
            for chunk in response.iter_content(chunk_size=1048576):
                if self.cancel_event.is_set():
                    raise RuntimeError("cancelled")
                if not chunk:
                    continue
                file.write(chunk)
                downloaded_size += len(chunk)
                if self.progress_callback:
                    elapsed = max(time.time() - start_time, 0.001)
                    speed = downloaded_size / elapsed
                    remaining = max(total_size - downloaded_size, 0)
                    eta = remaining / speed if speed > 0 else 0
                    self.progress_callback(
                        downloaded_size,
                        total_size,
                        file_id=job.database_key,
                        file_path=str(job.temp_path),
                        speed=speed,
                        eta=eta,
                    )

        if job.final_path.exists():
            job.final_path.unlink()
        os.rename(job.temp_path, job.final_path)
        final_size = job.final_path.stat().st_size
        self.history.record_completed(
            job.database_key,
            str(job.final_path),
            final_size,
            user_id=job.user_id,
            post_id=job.post_id,
        )
        return DownloadResult.completed(job.media_url, job.final_path, final_size)

    @staticmethod
    def _remove_temp(path: Path):
        if path.exists():
            path.unlink()
```

- [ ] **Step 4: Run engine tests**

Run:

```bash
pytest tests/downloader/test_download_engine.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add downloader/engine/download_engine.py tests/downloader/test_download_engine.py
git commit -m "feat: add shared synchronous download engine"
```

---

## Task 7: Add Coomer/Kemono Planner

**Files:**
- Create: `downloader/planners/coomer_kemono_planner.py`
- Test: `tests/downloader/test_coomer_kemono_planner.py`

- [ ] **Step 1: Write failing planner tests**

Create `tests/downloader/test_coomer_kemono_planner.py`:

```python
from pathlib import Path

from downloader.planners.coomer_kemono_planner import CoomerKemonoPlanner


def test_planner_creates_jobs_for_file_and_attachments(tmp_path):
    posts = [
        {
            "id": "123",
            "title": "Hello World",
            "published": "2025-01-01T00:00:00",
            "file": {"path": "/data/file.jpg", "name": "file.jpg"},
            "attachments": [
                {"path": "/data/video.mp4", "name": "video.mp4"},
                {"path": "", "name": "empty.jpg"},
            ],
        }
    ]
    planner = CoomerKemonoPlanner(
        download_folder=tmp_path,
        site="kemono.cr",
        service="patreon",
        user_id="creator",
        headers={"User-Agent": "test"},
    )

    jobs = planner.create_jobs(posts)

    assert len(jobs) == 2
    assert jobs[0].media_url == "https://kemono.cr/data/file.jpg"
    assert jobs[0].target_folder == tmp_path / "creator" / "images"
    assert jobs[0].post_id == "123"
    assert jobs[1].media_url == "https://kemono.cr/data/video.mp4"
    assert jobs[1].target_folder == tmp_path / "creator" / "videos"


def test_planner_deduplicates_urls(tmp_path):
    posts = [
        {
            "id": "123",
            "title": "Hello World",
            "published": "2025-01-01T00:00:00",
            "file": {"path": "/data/file.jpg", "name": "file.jpg"},
            "attachments": [{"path": "/data/file.jpg", "name": "file.jpg"}],
        }
    ]
    planner = CoomerKemonoPlanner(
        download_folder=tmp_path,
        site="kemono.cr",
        service="patreon",
        user_id="creator",
        headers={},
    )

    jobs = planner.create_jobs(posts)

    assert len(jobs) == 1
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/downloader/test_coomer_kemono_planner.py -v
```

Expected: FAIL because planner does not exist.

- [ ] **Step 3: Implement planner**

Create `downloader/planners/coomer_kemono_planner.py`:

```python
import os
from pathlib import Path
from urllib.parse import urljoin

from downloader.engine.download_filters import classify_extension
from downloader.models.download_job import DownloadJob


class CoomerKemonoPlanner:
    def __init__(
        self,
        *,
        download_folder: str | Path,
        site: str,
        service: str,
        user_id: str,
        headers: dict[str, str],
        folder_structure: str = "default",
    ):
        self.download_folder = Path(download_folder)
        self.site = site
        self.service = service
        self.user_id = user_id
        self.headers = headers
        self.folder_structure = folder_structure

    def create_jobs(self, posts: list[dict]) -> list[DownloadJob]:
        jobs = []
        seen = set()
        for post in posts:
            post_id = str(post.get("id") or "unknown_id")
            title = post.get("title") or ""
            published = post.get("published") or ""
            entries = []
            file_entry = post.get("file") or {}
            if file_entry.get("path"):
                entries.append(file_entry)
            entries.extend(post.get("attachments") or [])

            attachment_index = 0
            for entry in entries:
                media_path = entry.get("path")
                if not media_path:
                    continue
                media_url = self._make_media_url(media_path)
                if media_url in seen:
                    continue
                seen.add(media_url)
                attachment_index += 1
                filename = self._filename(entry, media_url, attachment_index)
                extension = os.path.splitext(filename)[1].lower()
                media_type = classify_extension(extension)
                jobs.append(
                    DownloadJob(
                        media_url=media_url,
                        target_folder=self._target_folder(media_type, post_id),
                        filename=filename,
                        domain="kemono" if "kemono" in self.site else "coomer",
                        headers=self.headers,
                        user_id=self.user_id,
                        post_id=post_id,
                        post_name=title,
                        post_time=published,
                        media_type=media_type,
                    )
                )
        return jobs

    def _make_media_url(self, media_path: str) -> str:
        if media_path.startswith("http://") or media_path.startswith("https://"):
            return media_path
        return urljoin(f"https://{self.site}", media_path)

    def _filename(self, entry: dict, media_url: str, attachment_index: int) -> str:
        raw_name = entry.get("name") or os.path.basename(media_url.split("?", 1)[0]) or "file"
        name, extension = os.path.splitext(raw_name)
        return f"{name}_{attachment_index}{extension}"

    def _target_folder(self, media_type: str, post_id: str) -> Path:
        folder_name = {
            "image": "images",
            "video": "videos",
            "compressed": "compressed",
            "document": "documents",
        }.get(media_type, "other")
        if self.folder_structure == "post_number":
            return self.download_folder / self.user_id / f"post_{post_id}" / folder_name
        return self.download_folder / self.user_id / folder_name
```

- [ ] **Step 4: Run planner tests**

Run:

```bash
pytest tests/downloader/test_coomer_kemono_planner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add downloader/planners/coomer_kemono_planner.py tests/downloader/test_coomer_kemono_planner.py
git commit -m "feat: add coomer kemono download planner"
```

---

## Task 8: Wire Coomer/Kemono Downloader To Planner And Engine

**Files:**
- Modify: `downloader/downloader.py`
- Modify: `app/adapters/downloader_factory.py`
- Test: `tests/test_downloader_factory.py`
- Test: `tests/downloader/test_coomer_kemono_integration.py`

- [ ] **Step 1: Write integration test using fake posts**

Create `tests/downloader/test_coomer_kemono_integration.py`:

```python
from downloader.downloader import Downloader


def test_downloader_collects_jobs_from_posts(tmp_path):
    downloader = Downloader(download_folder=str(tmp_path), max_workers=1)
    posts = [
        {
            "id": "1",
            "title": "Post",
            "published": "2025-01-01T00:00:00",
            "file": {"path": "/data/a.jpg", "name": "a.jpg"},
            "attachments": [{"path": "/data/b.mp4", "name": "b.mp4"}],
        }
    ]

    jobs = downloader.plan_coomer_kemono_jobs("kemono.cr", "creator", "patreon", posts)

    assert len(jobs) == 2
    assert jobs[0].domain == "kemono"
    assert jobs[0].user_id == "creator"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/downloader/test_coomer_kemono_integration.py -v
```

Expected: FAIL because `plan_coomer_kemono_jobs` does not exist.

- [ ] **Step 3: Add planning method to Downloader**

Modify `downloader/downloader.py` imports:

```python
from pathlib import Path
from downloader.planners.coomer_kemono_planner import CoomerKemonoPlanner
```

Add this method to `Downloader`:

```python
    def plan_coomer_kemono_jobs(self, site, user_id, service, posts):
        planner = CoomerKemonoPlanner(
            download_folder=Path(self.download_folder),
            site=site,
            service=service,
            user_id=user_id,
            headers=self.headers,
            folder_structure=self.folder_structure,
        )
        return planner.create_jobs(posts)
```

- [ ] **Step 4: Run integration test**

Run:

```bash
pytest tests/downloader/test_coomer_kemono_integration.py -v
```

Expected: PASS.

- [ ] **Step 5: Add engine construction method**

Modify `downloader/downloader.py` imports:

```python
from downloader.engine.download_engine import DownloadEngine
from downloader.engine.download_history import DownloadHistory
```

Add this method to `Downloader`:

```python
    def create_download_engine(self):
        return DownloadEngine(
            session=self.session,
            history=DownloadHistory(self.db_path),
            cancel_event=self.cancel_requested,
            max_retries=self.max_retries,
            retry_interval=self.retry_interval,
            request_timeout=self.request_timeout,
            progress_callback=self.update_progress_callback,
            log_callback=self.log_callback,
        )
```

- [ ] **Step 6: Add job execution method**

Add this method to `Downloader`:

```python
    def process_download_job(self, job):
        engine = self.create_download_engine()
        result = engine.download(job)
        if result.status == "completed":
            with self.file_lock:
                self.completed_files += 1
            if self.update_global_progress_callback:
                self.update_global_progress_callback(self.completed_files, self.total_files)
        elif result.status == "skipped":
            with self.file_lock:
                self.skipped_files.append(str(job.final_path))
        elif result.status == "failed":
            with self.file_lock:
                self.failed_files.append(job.media_url)
        return result
```

If comparing enum values fails, import `DownloadStatus` and compare against `DownloadStatus.COMPLETED`, `DownloadStatus.SKIPPED`, and `DownloadStatus.FAILED`.

- [ ] **Step 7: Change `download_media` to plan jobs then execute jobs**

Inside `download_media`, replace:

```python
            media_entries = self._collect_filtered_media(posts, site)
            self.total_files = len(media_entries)
            self.completed_files = 0

            futures = []
            for entry in media_entries:
```

with:

```python
            jobs = self.plan_coomer_kemono_jobs(site, user_id, service, posts)
            self.total_files = len(jobs)
            self.completed_files = 0

            futures = []
            for job in jobs:
```

Replace queued execution:

```python
                    self.process_media_element(...)
```

with:

```python
                    self.process_download_job(job)
```

Replace threaded execution:

```python
                    future = self.executor.submit(
                        self.process_media_element,
                        ...
                    )
```

with:

```python
                    future = self.executor.submit(self.process_download_job, job)
```

- [ ] **Step 8: Run Coomer/Kemono tests**

Run:

```bash
pytest tests/downloader/test_coomer_kemono_planner.py tests/downloader/test_coomer_kemono_integration.py tests/test_downloader_factory.py -v
```

Expected: PASS.

- [ ] **Step 9: Run broader downloader tests**

Run:

```bash
pytest tests/test_downloader_factory.py tests/test_main_controller.py tests/downloader -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add downloader/downloader.py tests/downloader/test_coomer_kemono_integration.py
git commit -m "refactor: route coomer kemono downloads through jobs"
```

---

## Task 9: Migrate SimpCity To Shared Engine

**Files:**
- Modify: `downloader/simpcity.py`
- Test: `tests/test_simpcity_adapter.py`

- [ ] **Step 1: Add SimpCity job creation method test**

Add to `tests/test_simpcity_adapter.py`:

```python
from downloader.simpcity import SimpCity


def test_simpcity_creates_download_jobs(tmp_path):
    downloader = SimpCity(download_folder=str(tmp_path), max_workers=1)
    media_entries = [
        {
            "media_url": "https://example.com/a.jpg",
            "post_id": "10",
            "title": "Thread",
            "published": "2025-01-01",
            "filename": "a.jpg",
        }
    ]

    jobs = downloader.create_download_jobs("thread-folder", media_entries)

    assert len(jobs) == 1
    assert jobs[0].media_url == "https://example.com/a.jpg"
    assert jobs[0].target_folder == tmp_path / "thread-folder"
    assert jobs[0].filename == "a.jpg"
    assert jobs[0].domain == "simpcity"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_simpcity_adapter.py::test_simpcity_creates_download_jobs -v
```

Expected: FAIL because method does not exist.

- [ ] **Step 3: Add job creation method**

Modify `downloader/simpcity.py` imports:

```python
from pathlib import Path
from downloader.models.download_job import DownloadJob
```

Add to `SimpCity`:

```python
    def create_download_jobs(self, folder_name, media_entries):
        target_folder = Path(self.download_folder) / folder_name
        jobs = []
        for entry in media_entries:
            jobs.append(
                DownloadJob(
                    media_url=entry["media_url"],
                    target_folder=target_folder,
                    filename=entry.get("filename") or os.path.basename(entry["media_url"].split("?", 1)[0]),
                    domain="simpcity",
                    headers=self.headers,
                    post_id=entry.get("post_id"),
                    post_name=entry.get("title"),
                    post_time=entry.get("published"),
                )
            )
        return jobs
```

- [ ] **Step 4: Run SimpCity job test**

Run:

```bash
pytest tests/test_simpcity_adapter.py::test_simpcity_creates_download_jobs -v
```

Expected: PASS.

- [ ] **Step 5: Replace per-entry `process_media_element` calls with job execution**

In `download_images_from_simpcity`, replace manual `target_folder` and future creation with:

```python
            jobs = self.create_download_jobs(folder_name, media_entries)
            self.total_files = len(jobs)
            self.completed_files = 0
            futures = []

            for job in jobs:
                if self.download_mode == "queue":
                    self.process_download_job(job)
                else:
                    future = self.executor.submit(self.process_download_job, job)
                    futures.append(future)
```

If `process_download_job` is only on `Downloader`, move the method into `BaseApiDownloader` before this step.

- [ ] **Step 6: Run SimpCity tests**

Run:

```bash
pytest tests/test_simpcity_adapter.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add downloader/simpcity.py tests/test_simpcity_adapter.py
git commit -m "refactor: route simpcity downloads through shared jobs"
```

---

## Task 10: Move Shared Job Execution To BaseApiDownloader

**Files:**
- Modify: `downloader/core/base_api_downloader.py`
- Modify: `downloader/downloader.py`
- Test: `tests/test_downloader_factory.py`
- Test: `tests/downloader/test_download_engine.py`

- [ ] **Step 1: Add base downloader engine test**

Create `tests/downloader/test_base_api_downloader_engine.py`:

```python
from downloader.core.base_api_downloader import BaseApiDownloader


def test_base_api_downloader_has_engine_factory(tmp_path):
    downloader = BaseApiDownloader(download_folder=str(tmp_path), max_workers=1)

    engine = downloader.create_download_engine()

    assert engine.max_retries == downloader.max_retries
    assert engine.retry_interval == downloader.retry_interval
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/downloader/test_base_api_downloader_engine.py -v
```

Expected: FAIL if `create_download_engine` does not exist on `BaseApiDownloader`.

- [ ] **Step 3: Move engine methods to BaseApiDownloader**

Add imports to `downloader/core/base_api_downloader.py`:

```python
from downloader.engine.download_engine import DownloadEngine
from downloader.engine.download_history import DownloadHistory
from downloader.models.download_result import DownloadStatus
```

Add methods to `BaseApiDownloader`:

```python
    def create_download_engine(self):
        return DownloadEngine(
            session=self.session,
            history=DownloadHistory(self.db_path),
            cancel_event=self.cancel_requested,
            max_retries=self.max_retries,
            retry_interval=self.retry_interval,
            request_timeout=self.request_timeout,
            progress_callback=self.update_progress_callback,
            log_callback=self.log_callback,
        )

    def process_download_job(self, job):
        engine = self.create_download_engine()
        result = engine.download(job)
        if result.status == DownloadStatus.COMPLETED:
            with self.file_lock:
                self.completed_files += 1
            if self.update_global_progress_callback:
                self.update_global_progress_callback(self.completed_files, self.total_files)
        elif result.status == DownloadStatus.SKIPPED:
            with self.file_lock:
                self.skipped_files.append(str(job.final_path))
        elif result.status == DownloadStatus.FAILED:
            with self.file_lock:
                self.failed_files.append(job.media_url)
        return result
```

- [ ] **Step 4: Remove duplicate methods from `downloader/downloader.py`**

Delete `create_download_engine` and `process_download_job` from `downloader/downloader.py` if they were added there in Task 8.

- [ ] **Step 5: Run downloader tests**

Run:

```bash
pytest tests/downloader tests/test_downloader_factory.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add downloader/core/base_api_downloader.py downloader/downloader.py tests/downloader/test_base_api_downloader_engine.py
git commit -m "refactor: move shared job execution to base downloader"
```

---

## Task 11: Migrate Remaining Site Downloaders Incrementally

**Files:**
- Modify: `downloader/bunkr.py`
- Modify: `downloader/erome.py`
- Modify: `downloader/jpg5.py`
- Modify: `downloader/coomerfans.py`
- Tests: existing tests plus new site-specific job creation tests

- [ ] **Step 1: For each site, add a `create_download_jobs` test**

Use this pattern for each site-specific test:

```python
def test_site_creates_download_jobs(tmp_path):
    downloader = SiteDownloader(download_folder=str(tmp_path), max_workers=1)
    media_entries = [
        {
            "media_url": "https://example.com/file.jpg",
            "filename": "file.jpg",
            "post_id": "post",
            "title": "Title",
            "published": "2025-01-01",
        }
    ]

    jobs = downloader.create_download_jobs("target", media_entries)

    assert len(jobs) == 1
    assert jobs[0].media_url == "https://example.com/file.jpg"
    assert jobs[0].filename == "file.jpg"
```

- [ ] **Step 2: Implement `create_download_jobs` on one site only**

Do Bunkr first, then run Bunkr tests. Do not migrate multiple sites in one commit.

- [ ] **Step 3: Replace `process_media_element` calls for that site**

Replace each threaded call:

```python
future = self.executor.submit(self.process_media_element, ...)
```

with:

```python
future = self.executor.submit(self.process_download_job, job)
```

- [ ] **Step 4: Run site tests**

Run:

```bash
pytest tests -k bunkr -v
```

Expected: PASS.

- [ ] **Step 5: Commit Bunkr migration**

```bash
git add downloader/bunkr.py tests
git commit -m "refactor: route bunkr downloads through shared jobs"
```

- [ ] **Step 6: Repeat for Erome**

Run:

```bash
pytest tests -k erome -v
```

Commit:

```bash
git add downloader/erome.py tests
git commit -m "refactor: route erome downloads through shared jobs"
```

- [ ] **Step 7: Repeat for JPG5**

Run:

```bash
pytest tests -k jpg5 -v
```

Commit:

```bash
git add downloader/jpg5.py tests
git commit -m "refactor: route jpg5 downloads through shared jobs"
```

- [ ] **Step 8: Repeat for CoomerFans**

Run:

```bash
pytest tests -k coomerfans -v
```

Commit:

```bash
git add downloader/coomerfans.py tests
git commit -m "refactor: route coomerfans downloads through shared jobs"
```

---

## Task 12: Remove Legacy Duplicate Download Paths

**Files:**
- Modify: `downloader/downloader.py`
- Modify: `downloader/core/base_api_downloader.py`
- Test: all tests

- [ ] **Step 1: Find legacy call sites**

Run:

```bash
rg "process_media_element|safe_request\\(" downloader app tests
```

Expected: Only legacy helper definitions or no production call sites remain.

- [ ] **Step 2: Delete unused legacy methods**

Delete old methods only after `rg` confirms no migrated site calls them:

```python
process_media_element
safe_request
_find_valid_subdomain
```

Keep any method still used by an unmigrated site.

- [ ] **Step 3: Run full test suite**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 4: Run app import smoke test**

Run:

```bash
python -c "from app.views.pyside.main_window import MainWindow; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 5: Commit cleanup**

```bash
git add downloader app tests
git commit -m "refactor: remove legacy duplicate download paths"
```

---

## Task 13: Manual GUI Verification

**Files:**
- No code changes unless a bug is found.

- [ ] **Step 1: Launch the app**

Run:

```bash
python main.py
```

Expected: PySide UI opens.

- [ ] **Step 2: Verify invalid URL**

Enter:

```text
https://example.com/not-supported
```

Expected: UI logs invalid URL and re-enables controls.

- [ ] **Step 3: Verify Coomer/Kemono post URL**

Use a small known public post URL.

Expected:
- URL is recognized as `coomer_kemono`.
- Files are planned.
- Progress updates per file.
- Completed files are recorded in `resources/config/downloads.db`.
- Re-running skips already downloaded files.

- [ ] **Step 4: Verify SimpCity single-page mode**

Use a known SimpCity thread and enable “only this URL”.

Expected:
- Only current page is processed.
- Files are saved into the thread folder.
- Cancel button stops pending downloads.

- [ ] **Step 5: Verify Bunkr/Erome/JPG5/CoomerFans smoke flows**

Use one small URL per migrated site.

Expected:
- URL dispatch still works.
- Files download or skip cleanly.
- Progress and final logs are sane.

- [ ] **Step 6: Record verification notes**

Add a short note to the PR or commit summary:

```text
Manual verification:
- Coomer/Kemono post: pass
- Coomer/Kemono rerun skip: pass
- SimpCity single page: pass
- Bunkr/Erome/JPG5/CoomerFans smoke: pass
```

---

## Task 14: Documentation Update

**Files:**
- Modify: `README.md`
- Optional Modify: `docs/architecture.md`

- [ ] **Step 1: Add architecture note**

Create `docs/architecture.md` if it does not exist:

```markdown
# CoomerDL Architecture

CoomerDL uses a PySide UI backed by a site registry and shared download engine.

## Flow

1. The UI builds a `DownloadRequest`.
2. `MainController` asks `SiteRegistry` to parse and classify the URL.
3. The selected site downloader fetches page or API metadata.
4. The site planner converts metadata into `DownloadJob` objects.
5. `DownloadEngine` downloads each job, using temp files, resume headers, retry settings, SQLite history, and progress callbacks.

## Key Files

- `app/services/site_registry.py`: URL-to-site matching.
- `downloader/models/download_job.py`: normalized download job model.
- `downloader/engine/download_engine.py`: shared file transfer engine.
- `downloader/engine/download_history.py`: SQLite download history.
- `downloader/planners/coomer_kemono_planner.py`: Coomer/Kemono post-to-job conversion.
```

- [ ] **Step 2: Link architecture doc from README**

Add under README feature or development section:

```markdown
## Architecture

Downloader internals are documented in [docs/architecture.md](docs/architecture.md).
```

- [ ] **Step 3: Run docs sanity check**

Run:

```bash
python -c "from pathlib import Path; assert Path('docs/architecture.md').exists(); print('docs ok')"
```

Expected: prints `docs ok`.

- [ ] **Step 4: Commit docs**

```bash
git add README.md docs/architecture.md
git commit -m "docs: document downloader architecture"
```

---

## Risk Register

- Coomer/Kemono URL and file server behavior changes often. Keep the current subdomain fallback behavior until shared engine parity is proven.
- GUI progress callbacks are sensitive. Every engine migration must verify `update_progress_callback` and `update_global_progress_callback`.
- Cancellation behavior can regress when replacing direct `process_media_element` calls. Each migrated site needs a cancel smoke test.
- SQLite history uses `media_url` uniqueness today. If planners change URLs from relative to absolute, skip behavior may change. Preserve the exact final URL as the database key.
- Cyberdrop-DL is GPL-licensed; borrow architecture ideas, not source code.

## Recommended Timeline

- Tasks 1-2: 0.5 day
- Tasks 3-6: 1-2 days
- Tasks 7-8: 1-2 days
- Tasks 9-11: 3-6 days depending on site quirks
- Tasks 12-14: 1-2 days

Total expected effort: 7-12 focused working days for a careful migration, or 2-4 weeks with manual testing, review, and fixes.

## Final Verification

Run:

```bash
pytest -v
python -c "from app.services.site_registry import build_default_site_registry; print(build_default_site_registry().match('https://coomer.st/onlyfans/user/demo').handler.site_type)"
python -c "from downloader.models.download_job import DownloadJob; print('download job ok')"
```

Expected:

```text
all pytest tests pass
coomer_kemono
download job ok
```

## Self-Review

- Spec coverage: The plan covers registry dispatch, normalized jobs, shared engine, KToolBox-style Coomer/Kemono planning, Cyberdrop-DL-style crawler separation in a lightweight form, migration of existing sites, tests, docs, and manual verification.
- Placeholder scan: No `TBD`, `TODO`, or unspecified “handle edge cases” steps remain.
- Type consistency: `DownloadJob`, `DownloadResult`, `DownloadStatus`, `DownloadHistory`, `DownloadEngine`, `CoomerKemonoPlanner`, `SiteRegistry`, and `SiteHandler` are introduced before use.

