import threading

import pytest

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

    def iter_content(self, chunk_size=1):
        yield from self.chunks


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, stream=True, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers or {}})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class UrlRoutedSession:
    def __init__(self, responses_by_url):
        self.responses_by_url = responses_by_url
        self.calls = []

    def get(self, url, stream=True, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers or {}})
        response = self.responses_by_url[url].pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_job(tmp_path):
    return DownloadJob(
        media_url="https://example.com/file.jpg",
        target_folder=tmp_path,
        filename="file.jpg",
        domain="example",
    )


def test_engine_downloads_file_and_records_history(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")
    engine = DownloadEngine(FakeSession([FakeResponse([b"abc"])]), history, max_retries=0)

    result = engine.download(make_job(tmp_path))

    assert result.status == DownloadStatus.COMPLETED
    assert (tmp_path / "file.jpg").read_bytes() == b"abc"
    assert history.contains("https://example.com/file.jpg") is True


def test_engine_skips_existing_history_record(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")
    history.record_completed("https://example.com/file.jpg", str(tmp_path / "file.jpg"), 3)
    session = FakeSession([])
    engine = DownloadEngine(session, history)

    result = engine.download(make_job(tmp_path))

    assert result.status == DownloadStatus.SKIPPED
    assert session.calls == []


def test_engine_retries_failed_request(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")
    session = FakeSession([Exception("boom"), FakeResponse([b"ok"])])
    engine = DownloadEngine(session, history, max_retries=1, retry_interval=0)

    result = engine.download(make_job(tmp_path))

    assert result.status == DownloadStatus.COMPLETED
    assert len(session.calls) == 2


def test_engine_cancels_before_request(tmp_path):
    cancel_event = threading.Event()
    cancel_event.set()
    engine = DownloadEngine(FakeSession([]), DownloadHistory(tmp_path / "downloads.db"), cancel_event=cancel_event)

    result = engine.download(make_job(tmp_path))

    assert result.status == DownloadStatus.CANCELLED


def test_engine_resumes_partial_temp_file(tmp_path):
    job = make_job(tmp_path)
    job.temp_path.write_bytes(b"abc")
    history = DownloadHistory(tmp_path / "downloads.db")
    session = FakeSession([FakeResponse([b"def"], headers={"content-length": "3"})])
    engine = DownloadEngine(session, history, max_retries=0)

    result = engine.download(job)

    assert result.status == DownloadStatus.COMPLETED
    assert job.final_path.read_bytes() == b"abcdef"
    assert session.calls[0]["headers"]["Range"] == "bytes=3-"


def test_engine_falls_back_to_coomer_data_subdomain_after_404(tmp_path):
    job = DownloadJob(
        media_url="https://coomer.st/ab/cd/file.jpg",
        target_folder=tmp_path,
        filename="file.jpg",
        domain="coomer",
    )
    session = UrlRoutedSession(
        {
            "https://coomer.st/ab/cd/file.jpg": [FakeResponse([], status_code=404)],
            "https://n1.coomer.st/data/ab/cd/file.jpg": [
                FakeResponse([b""], headers={"content-length": "0"}),
                FakeResponse([b"image"], headers={"content-length": "5"}),
            ],
        }
    )
    engine = DownloadEngine(session, DownloadHistory(tmp_path / "downloads.db"), max_retries=0)

    result = engine.download(job)

    assert result.status == DownloadStatus.COMPLETED
    assert job.final_path.read_bytes() == b"image"
    assert [call["url"] for call in session.calls] == [
        "https://coomer.st/ab/cd/file.jpg",
        "https://n1.coomer.st/data/ab/cd/file.jpg",
        "https://n1.coomer.st/data/ab/cd/file.jpg",
    ]


def test_engine_falls_back_to_coomer_data_subdomain_after_request_error(tmp_path):
    job = DownloadJob(
        media_url="https://coomer.st/ab/cd/file.jpg",
        target_folder=tmp_path,
        filename="file.jpg",
        domain="coomer",
    )
    session = UrlRoutedSession(
        {
            "https://coomer.st/ab/cd/file.jpg": [Exception("redirect target timed out")],
            "https://n1.coomer.st/data/ab/cd/file.jpg": [
                FakeResponse([b""], headers={"content-length": "0"}),
                FakeResponse([b"image"], headers={"content-length": "5"}),
            ],
        }
    )
    engine = DownloadEngine(session, DownloadHistory(tmp_path / "downloads.db"), max_retries=0)

    result = engine.download(job)

    assert result.status == DownloadStatus.COMPLETED
    assert job.final_path.read_bytes() == b"image"


def test_engine_logs_coomer_fallback_probe_failures(tmp_path):
    job = DownloadJob(
        media_url="https://coomer.st/ab/cd/file.jpg",
        target_folder=tmp_path,
        filename="file.jpg",
        domain="coomer",
    )
    session = UrlRoutedSession(
        {
            "https://coomer.st/ab/cd/file.jpg": [Exception("redirect target timed out")],
            **{
                f"https://n{i}.coomer.st/data/ab/cd/file.jpg": [Exception("probe timed out")]
                for i in range(1, 11)
            },
        }
    )
    messages = []
    engine = DownloadEngine(
        session,
        DownloadHistory(tmp_path / "downloads.db"),
        max_retries=0,
        log_callback=lambda domain, message: messages.append((domain, message)),
    )

    result = engine.download(job)

    assert result.status == DownloadStatus.FAILED
    assert any("CK_MEDIA_REQUEST_FAILED" in message for _, message in messages)
    assert any("CK_MEDIA_PROBE_FAILED" in message for _, message in messages)
    assert any("CK_MEDIA_FALLBACK_EXHAUSTED" in message for _, message in messages)


def test_engine_rejects_html_response_for_video_filename(tmp_path):
    job = DownloadJob(
        media_url="https://example.com/file",
        target_folder=tmp_path,
        filename="video.mp4",
        domain="example",
    )
    response = FakeResponse(
        [b"<!DOCTYPE html><html></html>"],
        headers={"content-length": "28", "content-type": "text/html; charset=utf-8"},
    )
    engine = DownloadEngine(FakeSession([response]), DownloadHistory(tmp_path / "downloads.db"), max_retries=0)

    result = engine.download(job)

    assert result.status == DownloadStatus.FAILED
    assert not job.final_path.exists()


def test_engine_corrects_image_payload_extension_when_filename_is_video(tmp_path):
    job = DownloadJob(
        media_url="https://example.com/file",
        target_folder=tmp_path,
        filename="clip.mp4",
        domain="example",
    )
    response = FakeResponse(
        [b"\xff\xd8\xff\xe0jpeg bytes"],
        headers={"content-length": "14", "content-type": "application/octet-stream"},
    )
    engine = DownloadEngine(FakeSession([response]), DownloadHistory(tmp_path / "downloads.db"), max_retries=0)

    result = engine.download(job)

    assert result.status == DownloadStatus.COMPLETED
    assert result.file_path == tmp_path / "clip.jpg"
    assert (tmp_path / "clip.jpg").read_bytes() == b"\xff\xd8\xff\xe0jpeg bytes"
    assert not job.final_path.exists()


def test_engine_corrects_mpeg_ts_payload_extension_when_filename_is_mp4(tmp_path):
    job = DownloadJob(
        media_url="https://example.com/file",
        target_folder=tmp_path,
        filename="clip.mp4",
        domain="example",
    )
    packet = b"\x47" + (b"\x00" * 187)
    response = FakeResponse(
        [packet * 3],
        headers={"content-length": str(len(packet) * 3), "content-type": "application/octet-stream"},
    )
    engine = DownloadEngine(FakeSession([response]), DownloadHistory(tmp_path / "downloads.db"), max_retries=0)

    result = engine.download(job)

    assert result.status == DownloadStatus.COMPLETED
    assert result.file_path == tmp_path / "clip.ts"
    assert (tmp_path / "clip.ts").read_bytes() == packet * 3
    assert not job.final_path.exists()
