import hashlib
import http.server
import socketserver
import threading

from downloader.adapters.pixeldrain_adapter import PixelDrainAdapter
from downloader.file_host import FileHostDownloader


MP4_BYTES = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    b"\x00\x00\x00\x08free"
)


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/file/video123/info":
            payload = (
                b'{"success": true, "id": "video123", "name": "fixture.mp4", '
                b'"mime_type": "video/mp4", "date_upload": "2026-05-26T00:00:00Z", '
                b'"hash_sha256": "fixture"}'
            )
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path == "/api/file/video123?download":
            self.send_response(200)
            self.send_header("content-type", "video/mp4")
            self.send_header("content-length", str(len(MP4_BYTES)))
            self.end_headers()
            self.wfile.write(MP4_BYTES)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


def test_file_host_downloader_downloads_valid_video_from_local_fixture(tmp_path):
    with socketserver.TCPServer(("127.0.0.1", 0), FixtureHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        adapter = PixelDrainAdapter(session=None)
        downloader = FileHostDownloader(
            adapter=adapter,
            download_folder=str(tmp_path),
            max_workers=1,
            max_retries=0,
            log_callback=lambda *args, **kwargs: None,
        )

        results = downloader.download_url(f"{base_url}/u/video123")
        server.shutdown()

    completed = [result for result in results if result.status.name == "COMPLETED"]
    assert len(completed) == 1
    file_path = completed[0].file_path
    assert file_path.exists()
    assert file_path.suffix == ".mp4"
    assert file_path.stat().st_size > 0
    assert hashlib.sha256(file_path.read_bytes()).hexdigest()
