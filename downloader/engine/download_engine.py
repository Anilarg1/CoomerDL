import os
import time
from pathlib import Path
from urllib.parse import urlparse

from downloader.models.download_job import DownloadJob
from downloader.models.download_result import DownloadResult


class DownloadEngine:
    def __init__(
        self,
        session,
        history,
        cancel_event=None,
        max_retries=3,
        retry_interval=1.0,
        request_timeout=(10, 120),
        progress_callback=None,
        log_callback=None,
    ):
        self.session = session
        self.history = history
        self.cancel_event = cancel_event
        self.max_retries = max(0, int(max_retries))
        self.retry_interval = retry_interval
        self.request_timeout = request_timeout
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.subdomain_cache = {}

    def _is_cancelled(self) -> bool:
        return bool(self.cancel_event and self.cancel_event.is_set())

    def _log(self, domain: str, message: str):
        if self.log_callback:
            try:
                self.log_callback(domain, message)
            except TypeError:
                self.log_callback(message)

    def _get(self, url: str, headers: dict[str, str], timeout=None):
        return self.session.get(
            url,
            stream=True,
            headers=headers or None,
            timeout=timeout or self.request_timeout,
        )

    def _request(self, job: DownloadJob, headers: dict[str, str]):
        domain = urlparse(job.media_url).netloc
        try:
            response = self._get(job.media_url, headers)
        except Exception as exc:
            if "coomer" not in domain and "kemono" not in domain:
                raise
            self._log(job.domain, f"CK_MEDIA_REQUEST_FAILED: {job.media_url} ({type(exc).__name__}: {exc})")
            alt_url = self._find_valid_subdomain(job.media_url, headers)
            if alt_url == job.media_url:
                self._log(job.domain, f"CK_MEDIA_FALLBACK_EXHAUSTED: {job.media_url}")
                raise
            self.subdomain_cache[job.media_url] = alt_url
            self._log(job.domain, f"CK_MEDIA_FALLBACK_SELECTED: {alt_url}")
            return self._get(alt_url, headers)

        if response.status_code in (403, 404) and ("coomer" in domain or "kemono" in domain):
            self._log(job.domain, f"CK_MEDIA_STATUS_FALLBACK: {response.status_code} {job.media_url}")
            alt_url = self.subdomain_cache.get(job.media_url)
            if alt_url is None:
                alt_url = self._find_valid_subdomain(job.media_url, headers)
                self.subdomain_cache[job.media_url] = alt_url

            if alt_url != job.media_url:
                self._log(job.domain, f"CK_MEDIA_FALLBACK_SELECTED: {alt_url}")
                return self._get(alt_url, headers)

            self._log(job.domain, f"CK_MEDIA_FALLBACK_EXHAUSTED: {job.media_url}")

        return response

    def _find_valid_subdomain(self, url: str, headers: dict[str, str], max_subdomains: int = 10) -> str:
        parsed = urlparse(url)
        original_path = parsed.path
        path = original_path
        if not original_path.startswith("/data/"):
            path = ("/data" + original_path) if not original_path.startswith("/data") else original_path

        host = parsed.netloc
        if "coomer" in host:
            base_domains = ["coomer.st"]
        elif "kemono" in host:
            base_domains = ["kemono.cr", "kemono.su"]
        else:
            base_domains = [host]

        for base in base_domains:
            for index in range(1, max_subdomains + 1):
                domain = f"n{index}.{base}"
                test_url = parsed._replace(netloc=domain, path=path).geturl()
                if self.progress_callback:
                    self.progress_callback(0, 0, status=f"Testing subdomain: {domain}")

                try:
                    response = self.session.get(
                        test_url,
                        stream=True,
                        headers=headers or None,
                        timeout=(3, 8),
                    )
                    self._log("system", f"CK_MEDIA_PROBE_RESULT: {test_url} -> {response.status_code}")
                    if response.status_code == 200:
                        return test_url
                except Exception as exc:
                    self._log(
                        "system",
                        f"CK_MEDIA_PROBE_FAILED: {test_url} ({type(exc).__name__}: {exc})",
                    )

        return url

    def _emit_progress(self, downloaded_size: int, total_size: int, job: DownloadJob, start_time: float):
        if not self.progress_callback:
            return
        elapsed = time.time() - start_time
        speed = downloaded_size / elapsed if elapsed > 0 else 0
        eta = (total_size - downloaded_size) / speed if speed > 0 and total_size > downloaded_size else 0
        self.progress_callback(
            downloaded_size,
            total_size,
            file_id=job.media_url,
            file_path=str(job.temp_path),
            speed=speed,
            eta=eta,
        )

    def _validate_response_media_type(self, response, job: DownloadJob):
        content_type = (response.headers.get("content-type") or "").lower()
        suffix = Path(job.filename).suffix.lower()
        media_suffixes = {
            ".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".wmv", ".flv",
            ".ts",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
            ".zip", ".rar", ".7z", ".tar", ".gz",
        }
        if suffix in media_suffixes and ("text/html" in content_type or "application/xhtml" in content_type):
            raise ValueError(f"HTML response received for media file {job.filename}")

    def _detect_media_extension(self, path: Path) -> str | None:
        with open(path, "rb") as file:
            header = file.read(1024)

        if header.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if header.startswith((b"GIF87a", b"GIF89a")):
            return ".gif"
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return ".webp"
        if len(header) >= 12 and header[4:8] == b"ftyp":
            return ".mp4"
        if header.startswith(b"\x1aE\xdf\xa3"):
            return ".webm"
        if len(header) >= 188 * 3 and all(header[index] == 0x47 for index in range(0, 188 * 3, 188)):
            return ".ts"
        return None

    def _corrected_final_path(self, job: DownloadJob) -> Path:
        detected_suffix = self._detect_media_extension(job.temp_path)
        if not detected_suffix:
            return job.final_path

        current_suffix = Path(job.filename).suffix.lower()
        equivalent_suffixes = {
            ".jpg": {".jpg", ".jpeg"},
            ".webm": {".webm", ".mkv"},
            ".mp4": {".mp4", ".m4v", ".mov"},
        }
        if current_suffix in equivalent_suffixes.get(detected_suffix, {detected_suffix}):
            return job.final_path

        corrected_path = job.final_path.with_suffix(detected_suffix)
        self._log(
            job.domain,
            f"MEDIA_EXTENSION_CORRECTED: {job.filename} -> {corrected_path.name}",
        )
        return corrected_path

    def download(self, job: DownloadJob) -> DownloadResult:
        if self._is_cancelled():
            return DownloadResult.cancelled(job.media_url)

        if self.history.contains(job.database_key):
            return DownloadResult.skipped(job.media_url, "already downloaded")

        job.target_folder.mkdir(parents=True, exist_ok=True)

        downloaded_size = job.temp_path.stat().st_size if job.temp_path.exists() else 0
        headers = dict(job.headers)
        if downloaded_size:
            headers["Range"] = f"bytes={downloaded_size}-"

        for attempt in range(self.max_retries + 1):
            if self._is_cancelled():
                return DownloadResult.cancelled(job.media_url)

            try:
                response = self._request(job, headers)
                response.raise_for_status()
                self._validate_response_media_type(response, job)

                content_length = int(response.headers.get("content-length", 0) or 0)
                total_size = downloaded_size + content_length if downloaded_size else content_length
                mode = "ab" if downloaded_size else "wb"
                start_time = time.time()

                with open(job.temp_path, mode + "") as file:
                    for chunk in response.iter_content(chunk_size=1048576):
                        if self._is_cancelled():
                            return DownloadResult.cancelled(job.media_url)
                        if chunk:
                            file.write(chunk)
                            downloaded_size += len(chunk)
                            self._emit_progress(downloaded_size, total_size, job, start_time)

                if total_size and downloaded_size < total_size:
                    headers["Range"] = f"bytes={downloaded_size}-"
                    continue

                final_path = self._corrected_final_path(job)
                if final_path.exists():
                    final_path.unlink()
                os.replace(job.temp_path, final_path)
                self.history.record_completed(
                    job.database_key,
                    str(final_path),
                    downloaded_size,
                    user_id=job.user_id,
                    post_id=job.post_id,
                )
                return DownloadResult.completed(job.media_url, final_path, downloaded_size)

            except Exception as exc:
                if attempt >= self.max_retries:
                    self._log(
                        job.domain,
                        f"FAILED_TO_DOWNLOAD_AFTER_ATTEMPTS: {job.media_url} ({type(exc).__name__}: {exc})",
                    )
                    return DownloadResult.failed(job.media_url, str(exc))
                time.sleep(self.retry_interval)

        return DownloadResult.failed(job.media_url, "exhausted retries")
