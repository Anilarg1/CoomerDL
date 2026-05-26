from pathlib import Path

from downloader.core.base_api_downloader import BaseApiDownloader
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


def test_create_download_jobs_uniquifies_case_insensitive_filename_collisions(tmp_path):
    downloader = BaseApiDownloader(download_folder=str(tmp_path), max_workers=1)

    jobs = downloader.create_download_jobs(
        "folder",
        [
            {"media_url": "https://example.com/a", "filename": "FullSizeRender.MOV"},
            {"media_url": "https://example.com/b", "filename": "FullSizeRender.mov"},
        ],
        domain="example",
    )

    assert jobs[0].filename == "FullSizeRender.MOV"
    assert jobs[1].filename == "FullSizeRender_2.mov"


def test_create_download_jobs_respects_video_only_setting(tmp_path):
    downloader = BaseApiDownloader(
        download_folder=str(tmp_path),
        max_workers=1,
        download_images=False,
        download_videos=True,
    )

    jobs = downloader.create_download_jobs(
        "folder",
        [
            {"media_url": "https://example.com/image.jpg", "filename": "image.jpg"},
            {"media_url": "https://example.com/video.mp4", "filename": "video.mp4"},
        ],
        domain="example",
    )

    assert [job.filename for job in jobs] == ["video.mp4"]


def test_create_download_jobs_filters_by_filename_when_url_has_no_extension(tmp_path):
    downloader = BaseApiDownloader(
        download_folder=str(tmp_path),
        max_workers=1,
        download_images=False,
        download_videos=True,
    )

    jobs = downloader.create_download_jobs(
        "folder",
        [
            {"media_url": "https://example.com/download?id=image", "filename": "image.jpg"},
            {"media_url": "https://example.com/download?id=video", "filename": "video.mp4"},
        ],
        domain="example",
    )

    assert [job.filename for job in jobs] == ["video.mp4"]
