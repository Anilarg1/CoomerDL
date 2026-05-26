from unittest.mock import Mock

from downloader.file_host import FileHostDownloader


class FakeAdapter:
    site_name = "fakehost"

    def __init__(self):
        self.session = Mock()

    def resolve_url(self, url):
        return {
            "folder_name": "fake_folder",
            "media": [
                {
                    "media_url": "https://cdn.fake/file.mp4",
                    "filename": "file.mp4",
                    "title": "fake",
                    "post_id": None,
                    "published": "",
                }
            ],
        }


def test_file_host_downloader_uses_adapter_media_entries(tmp_path):
    downloader = FileHostDownloader(
        adapter=FakeAdapter(),
        download_folder=str(tmp_path),
        max_workers=1,
        log_callback=lambda *args, **kwargs: None,
    )

    jobs = downloader.resolve_jobs("https://fakehost.test/item")

    assert len(jobs) == 1
    assert jobs[0].domain == "fakehost"
    assert jobs[0].filename == "file.mp4"
    assert jobs[0].target_folder.name == "fake_folder"
