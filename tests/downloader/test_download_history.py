from downloader.engine.download_history import DownloadHistory


def test_history_records_and_finds_download(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")

    history.record_completed(
        media_url="https://example.com/file.jpg",
        file_path=str(tmp_path / "file.jpg"),
        file_size=123,
        user_id="user",
        post_id="post",
    )

    assert history.contains("https://example.com/file.jpg") is True
    assert history.get("https://example.com/file.jpg") == (str(tmp_path / "file.jpg"), 123)


def test_history_returns_false_for_unknown_download(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")

    assert history.contains("https://example.com/missing.jpg") is False
    assert history.get("https://example.com/missing.jpg") is None


def test_history_clear_removes_all_downloads(tmp_path):
    history = DownloadHistory(tmp_path / "downloads.db")
    history.record_completed("url", "path", 1)

    history.clear()

    assert history.contains("url") is False
