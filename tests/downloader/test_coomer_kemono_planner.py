from downloader.planners.coomer_kemono_planner import CoomerKemonoPlanner


def test_planner_creates_jobs_from_main_file_and_attachments(tmp_path):
    planner = CoomerKemonoPlanner(
        download_folder=tmp_path,
        site="kemono.cr",
        service="patreon",
        user_id="creator",
        headers={"Referer": "https://kemono.cr/"},
    )

    jobs = planner.create_jobs(
        [
            {
                "id": "1",
                "title": "Post",
                "published": "2025-01-01T00:00:00",
                "file": {"path": "/data/a.jpg", "name": "a.jpg"},
                "attachments": [{"path": "/data/b.mp4", "name": "b.mp4"}],
            }
        ]
    )

    assert [job.media_url for job in jobs] == [
        "https://kemono.cr/data/a.jpg",
        "https://kemono.cr/data/b.mp4",
    ]
    assert jobs[0].domain == "kemono"
    assert jobs[0].target_folder == tmp_path / "creator" / "images"
    assert jobs[1].target_folder == tmp_path / "creator" / "videos"
    assert jobs[0].headers == {"Referer": "https://kemono.cr/"}


def test_planner_filters_disabled_media_types(tmp_path):
    planner = CoomerKemonoPlanner(
        download_folder=tmp_path,
        site="coomer.st",
        service="onlyfans",
        user_id="creator",
        download_videos=False,
    )

    jobs = planner.create_jobs(
        [
            {
                "id": "1",
                "file": {"path": "/data/a.jpg"},
                "attachments": [{"path": "/data/b.mp4"}],
            }
        ]
    )

    assert len(jobs) == 1
    assert jobs[0].media_type == "image"


def test_planner_deduplicates_media_urls(tmp_path):
    planner = CoomerKemonoPlanner(tmp_path, "kemono.cr", "patreon", "creator")

    jobs = planner.create_jobs(
        [
            {
                "id": "1",
                "file": {"path": "/data/a.jpg"},
                "attachments": [{"path": "/data/a.jpg"}],
            }
        ]
    )

    assert len(jobs) == 1
