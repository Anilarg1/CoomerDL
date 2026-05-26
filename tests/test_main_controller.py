import unittest
from unittest.mock import Mock

from app.controllers.main_controller import MainController
from app.services.site_registry import build_default_site_registry
from app.services.url_service import UrlService


class FakeApp:
    def __init__(self):
        self.active_downloader = object()
        self.exported_downloader = None
        self.enabled = False
        self.url_service = UrlService()
        self.site_registry = build_default_site_registry(self.url_service)
        self.download_folder = "downloads"
        self.settings = {}
        self.app_state = Mock()

    def enable_widgets(self):
        self.enabled = True

    def export_logs(self):
        self.exported_downloader = self.active_downloader

    def tr(self, key, **kwargs):
        return key.format(**kwargs) if kwargs else key

    def add_log_message_safe(self, *args):
        pass

    def show_error(self, *args):
        pass

    def prepare_download_ui(self):
        pass


class MainControllerTests(unittest.TestCase):
    def test_controller_uses_registry_for_url_parsing(self):
        app = FakeApp()
        controller = MainController(app)

        parsed = controller.parse_request_url("https://coomer.st/onlyfans/user/abc123")

        self.assertEqual(parsed.site_type, "coomer_kemono")
        self.assertEqual(parsed.service, "onlyfans")
        self.assertEqual(parsed.user, "abc123")

    def test_wrapped_download_exports_logs_before_clearing_downloader(self):
        app = FakeApp()
        controller = MainController(app)

        controller.wrapped_download(lambda: None)

        self.assertIsNotNone(app.exported_downloader)
        self.assertIsNone(app.active_downloader)
        self.assertTrue(app.enabled)

    def test_controller_routes_file_hosts_to_file_host_downloader(self):
        for url, site_type in [
            ("https://pixeldrain.com/u/abc123", "pixeldrain"),
            ("https://turbo.cr/v/abc123", "turbovid"),
            ("https://gofile.io/d/abc123", "gofile"),
            ("https://filester.gg/d/fileSlug", "filester"),
        ]:
            with self.subTest(url=url):
                app = FakeApp()
                app.url_entry = Mock(get=Mock(return_value=url))
                app.download_images_check = Mock(get=Mock(return_value=True))
                app.download_videos_check = Mock(get=Mock(return_value=True))
                app.download_compressed_check = Mock(get=Mock(return_value=True))
                app.only_this_url_check = Mock(get=Mock(return_value=True))
                app.setup_file_host_downloader = Mock()
                app.file_host_downloader = Mock()
                app.file_host_downloader.download_url = Mock()

                MainController(app).start_download()

                app.setup_file_host_downloader.assert_called_once_with(site_type)


if __name__ == "__main__":
    unittest.main()
