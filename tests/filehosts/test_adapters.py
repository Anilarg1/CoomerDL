from unittest.mock import Mock

from bs4 import BeautifulSoup

from downloader.adapters.filester_adapter import FilesterAdapter
from downloader.adapters.gofile_adapter import GoFileAdapter
from downloader.adapters.jpg5_adapter import Jpg5Adapter
from downloader.adapters.pixeldrain_adapter import PixelDrainAdapter
from downloader.adapters.turbovid_adapter import TurboVidAdapter


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload
        self.text = ""
        self.content = b""
        self.headers = {}

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_pixeldrain_file_resolves_api_download_url():
    session = Mock()
    session.get.return_value = JsonResponse({
        "success": True,
        "id": "abc123",
        "name": "clip.mp4",
        "mime_type": "video/mp4",
        "date_upload": "2026-05-26T00:00:00Z",
        "hash_sha256": "hash",
    })
    adapter = PixelDrainAdapter(session=session)

    result = adapter.resolve_url("https://pixeldrain.com/u/abc123")

    assert result["folder_name"] == "pixeldrain_abc123"
    assert result["media"][0]["media_url"] == "https://pixeldrain.com/api/file/abc123?download"
    assert result["media"][0]["filename"] == "clip.mp4"


def test_turbovid_video_uses_signed_download_url():
    session = Mock()
    session.get.return_value = JsonResponse({"filename": "signed.mp4", "url": "https://cdn.turbo.cr/data/abc123.mp4"})
    adapter = TurboVidAdapter(session=session)

    result = adapter.resolve_url("https://turbo.cr/v/abc123")

    assert result["folder_name"] == "turbovid_abc123"
    assert result["media"][0]["media_url"] == "https://cdn.turbo.cr/data/abc123.mp4"
    assert result["media"][0]["filename"] == "signed.mp4"


def test_gofile_folder_resolves_file_children():
    session = Mock()
    session.post.return_value = JsonResponse({"status": "ok", "data": {"token": "token"}})
    session.get.return_value = JsonResponse({
        "status": "ok",
        "data": {
            "id": "folder",
            "name": "Folder",
            "type": "folder",
            "canAccess": True,
            "children": {
                "file1": {
                    "id": "file1",
                    "type": "file",
                    "name": "clip.mp4",
                    "link": "https://store.gofile.io/download/web/file1/clip.mp4",
                    "canAccess": True,
                    "createTime": 1770000000,
                }
            },
        },
        "metadata": {"hasNextPage": False},
    })
    adapter = GoFileAdapter(session=session)

    result = adapter.resolve_url("https://gofile.io/d/folder")

    assert result["folder_name"] == "Folder_folder"
    assert result["media"][0]["filename"] == "clip.mp4"
    assert result["media"][0]["media_url"] == "https://store.gofile.io/download/web/file1/clip.mp4"
    headers = session.get.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer token"
    assert headers["X-BL"] == "en-US"
    assert headers["X-Website-Token"]


def test_filester_file_uses_public_download_api():
    session = Mock()
    session.post.return_value = JsonResponse({"download_url": "/download/fileSlug/file.mp4"})
    adapter = FilesterAdapter(session=session)
    adapter._request_soup = Mock(return_value=BeautifulSoup("""
      <html><head><meta property="og:title" content="file.mp4"></head>
      <body><div id="detailsContent">
        <span>MD5</span><span>abc</span>
        <span>Uploaded</span><span>2026-05-26</span>
        <span>Type</span><span>video/mp4</span>
      </div></body></html>
    """, "html.parser"))

    result = adapter.resolve_url("https://filester.si/d/fileSlug")

    assert result["folder_name"] == "filester_fileSlug"
    assert result["media"][0]["filename"] == "file.mp4"
    assert result["media"][0]["media_url"].endswith("/download/fileSlug/file.mp4?download=true")


def test_jpg5_adapter_supports_jpg6_single_media_page():
    session = Mock()
    adapter = Jpg5Adapter(session=session)
    adapter._request_soup = Mock(return_value=BeautifulSoup("""
      <div class="header-content-right">
        <a class="btn btn-download default" href="https://simp6.cuckcapital.cr/images3/image.jpg">Download</a>
      </div>
    """, "html.parser"))

    result = adapter.resolve_url("https://jpg6.su/img/img-7641.No98SXI")

    assert result["folder_name"] == "img_img-7641.No98SXI"
    assert result["media"][0]["media_url"] == "https://simp6.cuckcapital.cr/images3/image.jpg"
    assert result["media"][0]["filename"] == "image.jpg"


def test_jpg5_adapter_decodes_encrypted_download_href():
    encrypted = (
        "MWIxMTE4MDQxYTU2NDA1OTE2MWExZTE5NWI1ZTAwMWMxNzEyMjMxMjE5MDQwNDAyMDU1"
        "YTFhMWE0ZTFkMDgxMjE0MDYwMTUyNWY1YzQ0NDMwYjU0NWU0YzU5MzM1NjQ2MDY0"
        "NjRiMGIwZTQ2NTU1MTQ2NGQ3MjQ1MGI1ODE2MDU1MTRjNGI1ZTU3MTY1ZDE2MTA1"
        "NjEzNTc0NDUyNDM0NzQxMDY1ZjQ1MGE1YjVkNDQ1NTQ1MTU1MDBjNDM0ZDAzMDQxZQ=="
    )
    session = Mock()
    adapter = Jpg5Adapter(session=session)
    adapter._request_soup = Mock(return_value=BeautifulSoup(f"""
      <div class="header-content-right">
        <a class="btn btn-download default" href="{encrypted}">Download</a>
      </div>
    """, "html.parser"))

    result = adapter.resolve_url("https://jpg6.su/img/example")

    assert result["media"][0]["media_url"] == "https://simp6.cuckcapital.cr/images3/960x1280_90c58bc6682426b5ff88266b8ec5a647142c31c72206f9a3.jpg"
