from pathlib import Path
from unittest.mock import Mock

from downloader.engine.aria2_engine import Aria2Engine
from downloader.engine.download_history import DownloadHistory
from downloader.models.download_job import DownloadJob
from downloader.models.download_result import DownloadStatus


def test_aria2_engine_writes_queue_file_when_executable_is_missing(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")
    engine = Aria2Engine(
        history=history,
        executable_finder=lambda _: None,
        queue_folder=tmp_path / "queues",
    )
    job = DownloadJob(
        media_url="https://example.com/video.mp4?token=1",
        target_folder=tmp_path / "downloads",
        filename="video.mp4",
        domain="example",
        headers={"Referer": "https://example.com/"},
    )

    result = engine.download(job)

    assert result.status == DownloadStatus.FAILED
    assert "aria2c was not found" in result.message
    queue_file = tmp_path / "queues" / "aria2_queue.txt"
    assert queue_file.exists()
    queue_text = queue_file.read_text(encoding="utf-8")
    assert "https://example.com/video.mp4?token=1" in queue_text
    assert "  dir=" + str(job.target_folder) in queue_text
    assert "  out=video.mp4" in queue_text
    assert "  header=Referer: https://example.com/" in queue_text


def test_aria2_engine_runs_executable_and_records_completed_download(tmp_path):
    output_file = tmp_path / "downloads" / "video.mp4"

    def fake_runner(command, **kwargs):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        return Mock(returncode=0, stdout="ok", stderr="")

    history = DownloadHistory(tmp_path / "downloads.db")
    engine = Aria2Engine(
        history=history,
        executable_finder=lambda _: "C:/tools/aria2c.exe",
        command_runner=fake_runner,
    )
    job = DownloadJob(
        media_url="https://example.com/video.mp4",
        target_folder=output_file.parent,
        filename=output_file.name,
        domain="example",
        headers={"User-Agent": "Test UA"},
    )

    result = engine.download(job)

    assert result.status == DownloadStatus.COMPLETED
    assert result.file_path == output_file
    assert result.file_size == output_file.stat().st_size
    assert history.contains(job.database_key)


def test_aria2_engine_uses_integer_retry_wait_option(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")
    engine = Aria2Engine(history=history, retry_interval=1.5)
    job = DownloadJob(
        media_url="https://example.com/video.mp4",
        target_folder=tmp_path,
        filename="video.mp4",
        domain="example",
    )

    command = engine._build_command("aria2c", job)

    assert "--retry-wait=2" in command
