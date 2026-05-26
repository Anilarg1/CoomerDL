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

        self.assertIn("Total downloaded files: 2", content)
        self.assertIn("Failed files:\nfailed.jpg", content)
        self.assertIn("Skipped files:\nskipped.jpg", content)


if __name__ == "__main__":
    unittest.main()
