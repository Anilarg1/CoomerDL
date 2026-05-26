from unittest.mock import Mock

from bs4 import BeautifulSoup

from downloader.adapters.bunkr_adapter import BunkrAdapter


class FakeJsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_bunkr_profile_media_resolves_f_links_through_file_resolver():
    adapter = BunkrAdapter(session=Mock())
    adapter._resolve_f_url = Mock(
        return_value={
            "folder_name": "bunkr_post",
            "media": [{"media_url": "https://cdn.bunkr.test/video.mp4"}],
        }
    )
    grid = BeautifulSoup(
        """
        <div class="grid-images">
          <a class="after:absolute after:z-10 after:inset-0" href="/f/abc123"></a>
        </div>
        """,
        "html.parser",
    ).div

    media = adapter._resolve_profile_media("https://bunkr.cr/a/example", grid)

    assert media == [{"media_url": "https://cdn.bunkr.test/video.mp4"}]
    adapter._resolve_f_url.assert_called_once_with("https://bunkr.cr/f/abc123")


def test_bunkr_f_url_returns_direct_download_anchor_when_available():
    session = Mock()
    session.post.return_value = FakeJsonResponse(
        {
            "encrypted": True,
            "timestamp": 1779792480,
            "url": "OzE3IjZucGQmbStVF0dQXFh9Njd9JzFvfnU7bwMUAwsOAH5xImEkeWcuJj1yB11RVghTYCRwZyRncQYVbQ==",
        }
    )
    adapter = BunkrAdapter(session=session)
    adapter._request_soup = Mock(
        return_value=BeautifulSoup(
            """
            <html>
              <body>
                <h1 class="text-subs font-semibold text-base sm:text-lg truncate">19-07-2024.mp4</h1>
                <a class="btn btn-main btn-lg rounded-full px-6 font-semibold flex-1 ic-download-01 ic-before before:text-lg"
                   href="https://get.bunkrr.su/file/34970126">Download</a>
              </body>
            </html>
            """,
            "html.parser",
        )
    )

    result = adapter._resolve_f_url("https://bunkr.cr/f/YaRivo7oCksms")

    assert result["media"] == [
        {
            "media_url": "https://c4ta.scdn.st/be050b07-7866-4a3a-8ecd-3dee0e3a35a3.MP4",
            "filename": "19-07-2024.mp4",
            "title": "bunkr_post",
            "post_id": None,
            "published": "",
        }
    ]
