from pathlib import Path

from downloader.bunkr import BunkrDownloader
from downloader.coomerfans import CoomerfansDownloader
from downloader.erome import EromeDownloader
from downloader.jpg5 import Jpg5Downloader


def media_entries():
    return [
        {
            "media_url": "https://example.com/file.jpg",
            "filename": "file.jpg",
            "post_id": "post",
            "title": "Title",
            "published": "2025-01-01",
        }
    ]


def test_bunkr_creates_download_jobs(tmp_path):
    downloader = BunkrDownloader(download_folder=str(tmp_path), max_workers=1)

    jobs = downloader.create_download_jobs("target", media_entries())

    assert len(jobs) == 1
    assert jobs[0].media_url == "https://example.com/file.jpg"
    assert jobs[0].target_folder == tmp_path / "target"
    assert jobs[0].filename == "file.jpg"
    assert jobs[0].domain == "bunkr"


def test_erome_creates_download_jobs(tmp_path):
    downloader = EromeDownloader(download_folder=str(tmp_path), max_workers=1)

    jobs = downloader.create_download_jobs(tmp_path, media_entries())

    assert len(jobs) == 1
    assert jobs[0].target_folder == Path(tmp_path) / "erome_album"
    assert jobs[0].filename == "file.jpg"
    assert jobs[0].domain == "erome"


def test_jpg5_creates_download_jobs(tmp_path):
    downloader = Jpg5Downloader(url="https://jpg5.su/album/example", carpeta_destino=str(tmp_path), progress_manager=None)

    jobs = downloader.create_download_jobs("", media_entries())

    assert len(jobs) == 1
    assert jobs[0].target_folder == tmp_path
    assert jobs[0].filename == "file.jpg"
    assert jobs[0].domain == "jpg5"


def test_coomerfans_creates_download_jobs(tmp_path):
    downloader = CoomerfansDownloader(download_folder=str(tmp_path), max_workers=1)

    jobs = downloader.create_download_jobs(tmp_path, media_entries())

    assert len(jobs) == 1
    assert jobs[0].target_folder == Path(tmp_path) / "coomerfans_post"
    assert jobs[0].filename == "file.jpg"
    assert jobs[0].domain == "coomerfans"
