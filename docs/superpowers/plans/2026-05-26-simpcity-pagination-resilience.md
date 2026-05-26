# SimpCity Pagination Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make full SimpCity thread downloads resilient when later paginated pages fail, while preserving strict failure behavior for the first page and honoring the user's retry settings.

**Architecture:** Keep pagination responsibility inside `downloader/adapters/simpcity_adapter.py`, where thread pages are fetched and media is collected. Add a small retry wrapper for page fetches, tolerate failures only after at least one page has been successfully parsed, and return the media collected so far. Keep file download retry/concurrency behavior in `downloader/simpcity.py` and `BaseApiDownloader`.

**Tech Stack:** Python 3, `unittest`, `unittest.mock`, `requests`, `cloudscraper`, BeautifulSoup, existing PySide6 app services.

---

## Current Context

The current app has several relevant fixes already applied in the working tree:

- `app/adapters/downloader_factory.py` passes `max_workers`, `max_retries`, and `retry_interval` into `SimpCity`.
- `downloader/simpcity.py` accepts those retry settings and uses `self.adapter.scraper` as its download session so attachment requests use saved SimpCity cookies.
- `tests/test_downloader_factory.py` covers the SimpCity settings and cookie-session handoff.

The new problem is pagination-level failure:

```text
simpcity: Error while processing SimpCity thread: 500 Server Error: Internal Server Error for url: https://simpcity.cr/threads/corinna-kopf.3341/page-3
```

The workaround, enabling "Only this URL", works because it disables pagination. The desired behavior is full-thread downloading when possible, but without aborting already-collected media if a later page returns a transient server error.

## File Structure

Modify:

- `downloader/adapters/simpcity_adapter.py`
  - Add page-fetch retry behavior.
  - Add partial-result behavior for later-page failures.
  - Add clear logging for skipped/failed paginated pages.

- `downloader/simpcity.py`
  - Pass retry settings into the adapter so page-fetch retry count matches the downloader settings.

- `app/adapters/downloader_factory.py`
  - No new behavior expected if the previous retry-settings fix is present, but verify it still passes retry settings to `SimpCity`.

- `resources/config/i18n/en.json`
  - Add log message keys for page retry and partial pagination failure.

- `resources/config/i18n/es.json`
  - Add Spanish equivalents for the new log message keys.

- `tests/test_simpcity_adapter.py`
  - Create focused adapter tests for strict first-page failure, later-page partial results, and retry behavior.

- `tests/test_downloader_factory.py`
  - Keep existing tests; update only if constructor signatures require test fixtures to pass new adapter settings.

Do not restructure the downloader hierarchy. This change is intentionally scoped to SimpCity pagination.

---

### Task 1: Add Tests for Later-Page Partial Results

**Files:**
- Create: `tests/test_simpcity_adapter.py`
- Modify: none
- Test: `tests/test_simpcity_adapter.py`

- [ ] **Step 1: Create the test file with a helper adapter**

Create `tests/test_simpcity_adapter.py` with this content:

```python
import unittest
from unittest.mock import Mock

import requests

from downloader.adapters.simpcity_adapter import SimpCityAdapter


class SimpCityAdapterPaginationTests(unittest.TestCase):
    def make_adapter(self):
        adapter = SimpCityAdapter.__new__(SimpCityAdapter)
        adapter.cookies_path = "unused"
        adapter.log_callback = Mock()
        adapter.tr = lambda key, **kwargs: key.format(**kwargs) if kwargs else key
        adapter.title_selector = "h1[class=p-title-value]"
        adapter.posts_selector = "div[class*=message-main]"
        adapter.post_content_selector = "div[class*=message-userContent]"
        adapter.images_selector = "img[class*=bbImage]"
        adapter.videos_selector = "video source"
        adapter.attachments_block_selector = "section[class=message-attachments]"
        adapter.attachments_selector = "a"
        adapter.next_page_selector = "a[class*=pageNav-jump--next]"
        adapter.page_max_retries = 0
        adapter.page_retry_interval = 0
        return adapter

    def html(self, title="Thread Title", image="/images/a.jpg", next_href=None):
        next_link = f'<a class="pageNav-jump--next" href="{next_href}">Next</a>' if next_href else ""
        return f"""
        <html>
          <body>
            <h1 class="p-title-value">{title}</h1>
            <div class="message-main">
              <div class="message-userContent">
                <img class="bbImage" src="{image}" />
              </div>
            </div>
            {next_link}
          </body>
        </html>
        """

    def soup(self, html):
        from bs4 import BeautifulSoup

        return BeautifulSoup(html, "html.parser")

    def test_later_page_http_error_returns_media_collected_so_far(self):
        adapter = self.make_adapter()

        http_error = requests.HTTPError("500 Server Error")
        adapter.fetch_page = Mock(side_effect=[
            self.soup(self.html(
                image="/attachments/first.jpg",
                next_href="/threads/example.1/page-2",
            )),
            http_error,
        ])

        result = adapter.resolve_thread("https://simpcity.cr/threads/example.1/")

        self.assertEqual(result["folder_name"], "Thread Title")
        self.assertEqual(len(result["media"]), 1)
        self.assertEqual(
            result["media"][0]["media_url"],
            "https://simpcity.cr/attachments/first.jpg",
        )
        adapter.log_callback.assert_any_call(
            "simpcity",
            "SIMPCITY_PAGE_FAILED_USING_PARTIAL_RESULTS",
)
```

The expected log assertion will be refined after the implementation formats the message. For now, the important failing behavior is that `resolve_thread()` currently raises instead of returning one media item.

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_simpcity_adapter.SimpCityAdapterPaginationTests.test_later_page_http_error_returns_media_collected_so_far
```

Expected:

```text
ERROR
requests.exceptions.HTTPError: 500 Server Error
```

If it fails only because the log message includes formatted URL text, keep the failure and tighten the assertion in Task 5 after the translation key is available.

- [ ] **Step 3: Commit the failing test**

Do not commit if this is being implemented in an uncommitted local debugging session. If committing is desired:

```powershell
git add tests/test_simpcity_adapter.py
git commit -m "test: cover SimpCity partial pagination results"
```

---

### Task 2: Add Strict First-Page Failure Test

**Files:**
- Modify: `tests/test_simpcity_adapter.py`
- Test: `tests/test_simpcity_adapter.py`

- [ ] **Step 1: Add the strict first-page failure test**

Append this method to `SimpCityAdapterPaginationTests`:

```python
    def test_first_page_http_error_is_not_swallowed(self):
        adapter = self.make_adapter()
        http_error = requests.HTTPError("500 Server Error")
        adapter.fetch_page = Mock(side_effect=http_error)

        with self.assertRaises(requests.HTTPError):
            adapter.resolve_thread("https://simpcity.cr/threads/example.1/")
```

- [ ] **Step 2: Run the test and verify current behavior**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_simpcity_adapter.SimpCityAdapterPaginationTests.test_first_page_http_error_is_not_swallowed
```

Expected:

```text
OK
```

This test documents behavior we must preserve.

- [ ] **Step 3: Commit the strict failure test**

If committing:

```powershell
git add tests/test_simpcity_adapter.py
git commit -m "test: preserve strict SimpCity first page failures"
```

---

### Task 3: Add Partial Pagination Logging Keys

**Files:**
- Modify: `resources/config/i18n/en.json`
- Modify: `resources/config/i18n/es.json`
- Test: manual JSON parse or app import through tests

- [ ] **Step 1: Add English log messages**

In `resources/config/i18n/en.json`, add these keys near the existing SimpCity keys:

```json
"SIMPCITY_PAGE_FETCH_RETRY": "SimpCity page request failed for {url}. Retrying in {retry_interval}s. (Attempt {attempt}/{total})",
"SIMPCITY_PAGE_FAILED_USING_PARTIAL_RESULTS": "SimpCity page failed after retries: {url}. Downloading media collected so far.",
"SIMPCITY_PAGE_FAILED_NO_RESULTS": "SimpCity page failed before any media could be collected: {url}.",
```

Keep valid JSON commas based on the surrounding entries.

- [ ] **Step 2: Add Spanish log messages**

In `resources/config/i18n/es.json`, add:

```json
"SIMPCITY_PAGE_FETCH_RETRY": "La solicitud de la página de SimpCity falló para {url}. Reintentando en {retry_interval}s. (Intento {attempt}/{total})",
"SIMPCITY_PAGE_FAILED_USING_PARTIAL_RESULTS": "La página de SimpCity falló después de los reintentos: {url}. Descargando el contenido recopilado hasta ahora.",
"SIMPCITY_PAGE_FAILED_NO_RESULTS": "La página de SimpCity falló antes de recopilar contenido: {url}.",
```

- [ ] **Step 3: Verify JSON parses**

Run:

```powershell
.\.venv\Scripts\python.exe -m json.tool resources\config\i18n\en.json > $null
.\.venv\Scripts\python.exe -m json.tool resources\config\i18n\es.json > $null
```

Expected: both commands exit `0` with no output.

- [ ] **Step 4: Commit translation keys**

If committing:

```powershell
git add resources/config/i18n/en.json resources/config/i18n/es.json
git commit -m "chore: add SimpCity pagination log messages"
```

---

### Task 4: Implement Page Fetch Retry in SimpCityAdapter

**Files:**
- Modify: `downloader/adapters/simpcity_adapter.py`
- Test: `tests/test_simpcity_adapter.py`

- [ ] **Step 1: Add retry constructor parameters**

Change `SimpCityAdapter.__init__` signature from:

```python
def __init__(self, cookies_path="resources/config/cookies/simpcity.json", log_callback=None, tr=None):
```

to:

```python
def __init__(
    self,
    cookies_path="resources/config/cookies/simpcity.json",
    log_callback=None,
    tr=None,
    page_max_retries=3,
    page_retry_interval=2.0,
):
```

Inside `__init__`, before `self.set_cookies()`, add:

```python
self.page_max_retries = max(int(page_max_retries or 0), 0)
self.page_retry_interval = max(float(page_retry_interval or 0), 0.0)
```

- [ ] **Step 2: Import time and requests**

At the top of `downloader/adapters/simpcity_adapter.py`, change:

```python
import json
import os
import re
from urllib.parse import urljoin, urlparse
```

to:

```python
import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
```

- [ ] **Step 3: Add `_fetch_page_with_retries`**

Add this method below `fetch_page`:

```python
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
```

This intentionally only catches `requests.exceptions.RequestException`. Parser errors should still surface because they are code/data bugs, not transient HTTP failures.

- [ ] **Step 4: Run adapter tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_simpcity_adapter
```

Expected at this point:

- First-page strict test passes.
- Later-page partial test still fails until Task 5 changes `resolve_thread()`.

---

### Task 5: Implement Partial Results for Later Pagination Failures

**Files:**
- Modify: `downloader/adapters/simpcity_adapter.py`
- Test: `tests/test_simpcity_adapter.py`

- [ ] **Step 1: Update `resolve_thread()` page fetch**

Find this block in `resolve_thread()`:

```python
soup = self.fetch_page(current_url)
```

Replace it with:

```python
try:
    soup = self._fetch_page_with_retries(current_url)
except requests.exceptions.RequestException:
    if not all_media and folder_name is None:
        self.log("SIMPCITY_PAGE_FAILED_NO_RESULTS", url=current_url)
        raise

    self.log("SIMPCITY_PAGE_FAILED_USING_PARTIAL_RESULTS", url=current_url)
    break
```

- [ ] **Step 2: Tighten the partial-result test log assertion**

In `tests/test_simpcity_adapter.py`, replace:

```python
adapter.log_callback.assert_any_call(
    "simpcity",
    "SIMPCITY_PAGE_FAILED_USING_PARTIAL_RESULTS",
)
```

with:

```python
adapter.log_callback.assert_any_call(
    "simpcity",
    "SIMPCITY_PAGE_FAILED_USING_PARTIAL_RESULTS",
)
```

If the adapter translation formats the URL into the message, use:

```python
self.assertTrue(
    any(
        call.args[0] == "simpcity"
        and "https://simpcity.cr/threads/example.1/page-2" in call.args[1]
        for call in adapter.log_callback.call_args_list
    )
)
```

Use the second version if the first assertion fails after translation formatting.

- [ ] **Step 3: Run the targeted partial-result test**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_simpcity_adapter.SimpCityAdapterPaginationTests.test_later_page_http_error_returns_media_collected_so_far
```

Expected:

```text
OK
```

- [ ] **Step 4: Run all SimpCity adapter tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_simpcity_adapter
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit pagination partial-result behavior**

If committing:

```powershell
git add downloader/adapters/simpcity_adapter.py tests/test_simpcity_adapter.py
git commit -m "fix: keep SimpCity partial results when later pages fail"
```

---

### Task 6: Pass Retry Settings from SimpCity Downloader to Adapter

**Files:**
- Modify: `downloader/simpcity.py`
- Test: `tests/test_downloader_factory.py`

- [ ] **Step 1: Update `SimpCityAdapter` construction**

In `downloader/simpcity.py`, change:

```python
self.adapter = SimpCityAdapter(
    log_callback=self.log_callback,
    tr=self.tr,
)
```

to:

```python
self.adapter = SimpCityAdapter(
    log_callback=self.log_callback,
    tr=self.tr,
    page_max_retries=self.max_retries,
    page_retry_interval=self.retry_interval,
)
```

Keep this line after adapter construction:

```python
self.session = self.adapter.scraper
```

- [ ] **Step 2: Add a factory/constructor test for adapter retry settings**

In `tests/test_downloader_factory.py`, add:

```python
    def test_simpcity_adapter_receives_downloader_retry_settings(self):
        downloader = DownloaderFactory(
            FakeFrontend(),
            app=type("FakeApp", (), {"settings": {"max_retries": 4, "retry_interval": 2.0}})(),
        ).create_simpcity_downloader()

        self.assertEqual(downloader.adapter.page_max_retries, 4)
        self.assertEqual(downloader.adapter.page_retry_interval, 2.0)
```

- [ ] **Step 3: Run targeted factory tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_downloader_factory
```

Expected:

```text
OK
```

- [ ] **Step 4: Commit retry propagation**

If committing:

```powershell
git add downloader/simpcity.py tests/test_downloader_factory.py
git commit -m "fix: apply SimpCity retry settings to page pagination"
```

---

### Task 7: Add Test for Page Retry Before Partial Result

**Files:**
- Modify: `tests/test_simpcity_adapter.py`
- Test: `tests/test_simpcity_adapter.py`

- [ ] **Step 1: Add a test where page 2 fails once and succeeds**

Append:

```python
    def test_later_page_is_retried_before_partial_results(self):
        adapter = self.make_adapter()
        adapter.page_max_retries = 1
        adapter.page_retry_interval = 0

        transient_error = requests.HTTPError("500 Server Error")
        adapter.fetch_page = Mock(side_effect=[
            self.soup(self.html(
                image="/attachments/first.jpg",
                next_href="/threads/example.1/page-2",
            )),
            transient_error,
            self.soup(self.html(
                image="/attachments/second.jpg",
                next_href=None,
            )),
        ])

        result = adapter.resolve_thread("https://simpcity.cr/threads/example.1/")

        self.assertEqual(len(result["media"]), 2)
        self.assertEqual(
            [item["media_url"] for item in result["media"]],
            [
                "https://simpcity.cr/attachments/first.jpg",
                "https://simpcity.cr/attachments/second.jpg",
            ],
        )
```

- [ ] **Step 2: Run the retry test**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_simpcity_adapter.SimpCityAdapterPaginationTests.test_later_page_is_retried_before_partial_results
```

Expected:

```text
OK
```

- [ ] **Step 3: Commit retry test**

If committing:

```powershell
git add tests/test_simpcity_adapter.py
git commit -m "test: retry transient SimpCity pagination failures"
```

---

### Task 8: Improve Log Export Accuracy for Partial Downloads

**Files:**
- Modify: `app/services/log_service.py`
- Test: create or extend `tests/test_log_service.py`

Current exported summaries can show `Total de archivos descargados: 0` even when runtime logs show downloads, depending on downloader lifetime and export timing. This plan should not broaden scope into full reporting refactors, but partial pagination work benefits from accurate failed-file summaries.

- [ ] **Step 1: Add a focused LogService test**

Create `tests/test_log_service.py`:

```python
import tempfile
import unittest
from pathlib import Path

from app.services.log_service import LogService


class FakeDownloader:
    total_files = 2
    completed_files = 1
    skipped_files = ["skipped.jpg"]
    failed_files = ["failed.jpg"]


class LogServiceTests(unittest.TestCase):
    def test_export_logs_includes_downloader_counts_and_failed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = LogService(log_folder=tmp)
            path = service.export_logs(
                active_downloader=FakeDownloader(),
                download_images_enabled=True,
                download_videos_enabled=False,
            )

            content = Path(path).read_text(encoding="utf-8")

        self.assertIn("Total de archivos descargados: 2", content)
        self.assertIn("Archivos fallidos:\nfailed.jpg", content)
        self.assertIn("Archivos saltados:\nskipped.jpg", content)
```

- [ ] **Step 2: Run the test**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_log_service
```

Expected:

```text
OK
```

If it fails, investigate before changing production code. The controller export-order fix may already satisfy this.

- [ ] **Step 3: Commit only if needed**

If no production change is needed, commit the test:

```powershell
git add tests/test_log_service.py
git commit -m "test: cover exported downloader summary"
```

If production change is needed, include `app/services/log_service.py` in the commit.

---

### Task 9: Full Verification

**Files:**
- All modified files

- [ ] **Step 1: Run all unit tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Expected:

```text
OK
```

- [ ] **Step 2: Compile Python files**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall app downloader tests
```

Expected:

```text
Exit code 0
```

- [ ] **Step 3: Validate translation JSON**

Run:

```powershell
.\.venv\Scripts\python.exe -m json.tool resources\config\i18n\en.json > $null
.\.venv\Scripts\python.exe -m json.tool resources\config\i18n\es.json > $null
```

Expected:

```text
Exit code 0
```

- [ ] **Step 4: Inspect git diff**

Run:

```powershell
git diff -- downloader\adapters\simpcity_adapter.py downloader\simpcity.py app\adapters\downloader_factory.py resources\config\i18n\en.json resources\config\i18n\es.json tests
```

Expected:

- `SimpCityAdapter` retries page fetches.
- `SimpCityAdapter` raises on first-page failure.
- `SimpCityAdapter` returns partial media on later-page HTTP failures.
- `SimpCity` passes retry settings into the adapter.
- Tests cover the above behavior.

- [ ] **Step 5: Commit verification-ready implementation**

If committing:

```powershell
git add downloader\adapters\simpcity_adapter.py downloader\simpcity.py app\adapters\downloader_factory.py resources\config\i18n\en.json resources\config\i18n\es.json tests
git commit -m "fix: make SimpCity pagination resilient"
```

---

### Task 10: Manual App Verification

**Files:**
- No code changes

- [ ] **Step 1: Restart CoomerDL**

Run:

```powershell
Get-Process | Where-Object { $_.Path -eq 'C:\Users\shaai\CoomerDL\.venv\Scripts\python.exe' } | Stop-Process -Force
Start-Process -FilePath "C:\Users\shaai\CoomerDL\.venv\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "C:\Users\shaai\CoomerDL"
```

- [ ] **Step 2: Confirm settings**

In the app:

- Max downloads: `1`
- Max retries: `4`
- Retry interval: `2.0`
- SimpCity cookies: saved and current
- "Only this URL": off for full-thread test

- [ ] **Step 3: Test the known failing full thread**

Use:

```text
https://simpcity.cr/threads/corinna-kopf.3341/
```

Expected:

- The app processes page 1 and page 2 if reachable.
- If `/page-3` returns `500`, the log says the page failed and media collected so far will be downloaded.
- The run does not abort before attempting collected media downloads.

- [ ] **Step 4: Check newest log**

Run:

```powershell
$latest = Get-ChildItem -Path resources\config\logs -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $latest.FullName -Tail 120
```

Expected log pattern:

```text
simpcity: Processing SimpCity thread: https://simpcity.cr/threads/corinna-kopf.3341/
simpcity: SimpCity page request failed for https://simpcity.cr/threads/corinna-kopf.3341/page-3. Retrying in 2.0s. (Attempt 1/5)
simpcity: SimpCity page failed after retries: https://simpcity.cr/threads/corinna-kopf.3341/page-3. Downloading media collected so far.
simpcity: Starting download from ...
```

- [ ] **Step 5: Test first-page failure remains strict**

Use a clearly invalid or inaccessible SimpCity URL:

```text
https://simpcity.cr/threads/not-a-real-thread.000000/
```

Expected:

- The app logs the first-page error.
- It does not claim partial results.
- It does not download unrelated files.

---

## Rollback Plan

If the pagination change causes broad SimpCity failures:

1. Revert only `downloader/adapters/simpcity_adapter.py` and the new adapter tests.
2. Keep the previously fixed settings/session changes in `downloader/simpcity.py` unless they are proven to be the cause.
3. Re-run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall app downloader tests
```

4. Relaunch CoomerDL.

---

## Self-Review

- Spec coverage: The plan covers retrying page fetches, preserving strict first-page failures, returning partial results for later-page failures, logging the behavior, and verifying with the real problematic thread.
- Completeness scan: No deferred requirements or vague implementation steps remain. Each code-changing task includes concrete code.
- Type consistency: The plan uses existing `SimpCityAdapter`, `SimpCity`, `DownloaderFactory`, `page_max_retries`, and `page_retry_interval` names consistently.
- Scope check: This is a focused SimpCity pagination resilience change. It does not attempt unrelated downloader architecture refactors.
