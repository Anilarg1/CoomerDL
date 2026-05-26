from downloader.engine.download_filters import media_type_for_url, should_download_media


def test_media_type_for_known_extensions():
    assert media_type_for_url("https://example.com/a.jpg") == "image"
    assert media_type_for_url("https://example.com/a.mp4") == "video"
    assert media_type_for_url("https://example.com/a.zip") == "compressed"
    assert media_type_for_url("https://example.com/a.pdf") == "document"
    assert media_type_for_url("https://example.com/a.bin") == "other"


def test_should_download_media_respects_disabled_types():
    assert should_download_media("https://example.com/a.jpg", download_images=False) is False
    assert should_download_media("https://example.com/a.mp4", download_videos=False) is False
    assert should_download_media("https://example.com/a.zip", download_compressed=False) is False
    assert should_download_media("https://example.com/a.pdf", download_documents=False) is False
    assert should_download_media("https://example.com/a.bin", download_other=False) is False
