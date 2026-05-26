import unittest
from unittest.mock import patch

from app.adapters.downloader_factory import DownloaderFactory
from downloader.simpcity import SimpCity


class FakeFrontend:
    def get_download_folder(self):
        return "downloads"

    def get_max_downloads(self):
        return 1

    def log(self, *args, **kwargs):
        pass

    def enable_widgets(self):
        pass

    def update_progress(self, *args, **kwargs):
        pass

    def update_global_progress(self, *args, **kwargs):
        pass

    def get_tr(self):
        return None


class VideoOnlyFrontend(FakeFrontend):
    def get_download_images(self):
        return False

    def get_download_videos(self):
        return True

    def get_download_compressed(self):
        return False


class DownloaderFactoryTests(unittest.TestCase):
    def test_create_simpcity_downloader_uses_frontend_max_downloads(self):
        downloader = DownloaderFactory(FakeFrontend()).create_simpcity_downloader()

        self.assertEqual(downloader.max_workers, 1)

    def test_create_simpcity_downloader_uses_app_retry_settings(self):
        app = type(
            "FakeApp",
            (),
            {"settings": {"max_retries": 4, "retry_interval": 2.0}},
        )()

        downloader = DownloaderFactory(FakeFrontend(), app=app).create_simpcity_downloader()

        self.assertEqual(downloader.max_retries, 4)
        self.assertEqual(downloader.retry_interval, 2.0)

    def test_create_simpcity_downloader_uses_app_download_engine_setting(self):
        app = type(
            "FakeApp",
            (),
            {"settings": {"download_engine": "aria2"}},
        )()

        downloader = DownloaderFactory(FakeFrontend(), app=app).create_simpcity_downloader()

        self.assertEqual(downloader.download_engine, "aria2")

    def test_simpcity_adapter_receives_downloader_retry_settings(self):
        app = type(
            "FakeApp",
            (),
            {"settings": {"max_retries": 4, "retry_interval": 2.0}},
        )()

        downloader = DownloaderFactory(FakeFrontend(), app=app).create_simpcity_downloader()

        self.assertEqual(downloader.adapter.page_max_retries, 4)
        self.assertEqual(downloader.adapter.page_retry_interval, 2.0)

    def test_create_simpcity_downloader_uses_frontend_media_settings(self):
        downloader = DownloaderFactory(VideoOnlyFrontend()).create_simpcity_downloader()

        self.assertFalse(downloader.download_images)
        self.assertTrue(downloader.download_videos)

    def test_simpcity_uses_adapter_cookie_session_for_downloads(self):
        class FakeAdapter:
            def __init__(self, *args, **kwargs):
                self.scraper = object()

        with patch("downloader.simpcity.SimpCityAdapter", FakeAdapter):
            downloader = SimpCity(download_folder="downloads")

        self.assertIs(downloader.session, downloader.adapter.scraper)


if __name__ == "__main__":
    unittest.main()
