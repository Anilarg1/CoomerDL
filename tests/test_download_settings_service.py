from app.services.download_settings_service import DownloadSettingsService


def test_download_settings_parse_download_engine_label():
    service = DownloadSettingsService()

    parsed = service.parse_form_values(
        max_downloads_value="3",
        folder_structure_value="default",
        max_retries_value="4",
        retry_interval_value="2.0",
        file_naming_mode_label="Use File ID (default)",
        download_engine_label="aria2c",
    )

    assert parsed["download_engine"] == "aria2"


def test_download_settings_apply_download_engine_to_downloader():
    service = DownloadSettingsService()
    downloader = type("FakeDownloader", (), {})()

    service.apply_to_downloader(
        downloader,
        {
            "max_downloads": 3,
            "max_retries": 4,
            "retry_interval": 2.0,
            "file_naming_mode": 0,
            "download_engine": "aria2",
        },
    )

    assert downloader.download_engine == "aria2"
