from downloader.downloader import Downloader


def test_downloader_collects_jobs_from_posts(tmp_path):
    downloader = Downloader(download_folder=str(tmp_path), max_workers=1)
    posts = [
        {
            "id": "1",
            "title": "Post",
            "published": "2025-01-01T00:00:00",
            "file": {"path": "/data/a.jpg", "name": "a.jpg"},
            "attachments": [{"path": "/data/b.mp4", "name": "b.mp4"}],
        }
    ]

    jobs = downloader.plan_coomer_kemono_jobs("kemono.cr", "creator", "patreon", posts)

    assert len(jobs) == 2
    assert jobs[0].domain == "kemono"
    assert jobs[0].user_id == "creator"
