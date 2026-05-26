from downloader.core.base_api_downloader import BaseApiDownloader
from downloader.engine.aria2_engine import Aria2Engine


def test_base_api_downloader_has_engine_factory(tmp_path):
    downloader = BaseApiDownloader(download_folder=str(tmp_path), max_workers=1)

    engine = downloader.create_download_engine()

    assert engine.max_retries == downloader.max_retries
    assert engine.retry_interval == downloader.retry_interval


def test_base_api_downloader_can_create_aria2_engine(tmp_path):
    downloader = BaseApiDownloader(
        download_folder=str(tmp_path),
        max_workers=1,
        download_engine="aria2",
    )

    engine = downloader.create_download_engine()

    assert isinstance(engine, Aria2Engine)
    assert engine.max_retries == downloader.max_retries
    assert engine.retry_interval == downloader.retry_interval
