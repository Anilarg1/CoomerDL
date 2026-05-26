import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import requests

from downloader.simpcity import SimpCity
from downloader.adapters.simpcity_adapter import SimpCityAdapter


class SimpCityAdapterPaginationTests(unittest.TestCase):
    def test_simpcity_creates_download_jobs(self):
        with TemporaryDirectory() as tmp:
            downloader = SimpCity(download_folder=tmp, max_workers=1)
            media_entries = [
                {
                    "media_url": "https://example.com/a.jpg",
                    "post_id": "10",
                    "title": "Thread",
                    "published": "2025-01-01",
                    "filename": "a.jpg",
                }
            ]

            jobs = downloader.create_download_jobs("thread-folder", media_entries)

            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].media_url, "https://example.com/a.jpg")
            self.assertEqual(jobs[0].target_folder, Path(tmp) / "thread-folder")
            self.assertEqual(jobs[0].filename, "a.jpg")
            self.assertEqual(jobs[0].domain, "simpcity")

    def make_adapter(self):
        adapter = SimpCityAdapter.__new__(SimpCityAdapter)
        adapter.cookies_path = "unused"
        adapter.log_callback = Mock()
        adapter.tr = lambda key, **kwargs: key.format(**kwargs) if kwargs else key
        adapter.title_selector = "h1[class=p-title-value]"
        adapter.posts_selector = "div[class*=message-main]"
        adapter.post_content_selector = "div[class*=message-userContent]"
        adapter.images_selector = "img[class*=bbImage]"
        adapter.videos_selector = "video source, video[src]"
        adapter.attachments_block_selector = "section[class=message-attachments]"
        adapter.attachments_selector = "a"
        adapter.next_page_selector = "a[class*=pageNav-jump--next]"
        adapter.page_max_retries = 0
        adapter.page_retry_interval = 0
        adapter.bunkr_adapter = Mock()
        adapter.file_host_adapters = {}
        return adapter

    def html(self, title="Thread Title", image="/images/a.jpg", next_href=None):
        next_link = f'<a class="pageNav-jump--next" href="{next_href}">Next</a>' if next_href else ""
        return f"""
        <html>
          <body>
            <h1 class="p-title-value">{title}</h1>
            <div class="message-main">
              <div class="message-userContent">
                <img class="bbImage" src="{image}" />
              </div>
            </div>
            {next_link}
          </body>
        </html>
        """

    def soup(self, html):
        from bs4 import BeautifulSoup

        return BeautifulSoup(html, "html.parser")

    def test_later_page_http_error_returns_media_collected_so_far(self):
        adapter = self.make_adapter()

        http_error = requests.HTTPError("500 Server Error")
        adapter.fetch_page = Mock(side_effect=[
            self.soup(self.html(
                image="/attachments/first.jpg",
                next_href="/threads/example.1/page-2",
            )),
            http_error,
        ])

        result = adapter.resolve_thread("https://simpcity.cr/threads/example.1/")

        self.assertEqual(result["folder_name"], "Thread Title")
        self.assertEqual(len(result["media"]), 1)
        self.assertEqual(
            result["media"][0]["media_url"],
            "https://simpcity.cr/attachments/first.jpg",
        )
        adapter.log_callback.assert_any_call(
            "simpcity",
            "SIMPCITY_PAGE_FAILED_USING_PARTIAL_RESULTS",
        )

    def test_first_page_http_error_is_not_swallowed(self):
        adapter = self.make_adapter()
        http_error = requests.HTTPError("500 Server Error")
        adapter.fetch_page = Mock(side_effect=http_error)

        with self.assertRaises(requests.HTTPError):
            adapter.resolve_thread("https://simpcity.cr/threads/example.1/")

    def test_later_page_is_retried_before_partial_results(self):
        adapter = self.make_adapter()
        adapter.page_max_retries = 1
        adapter.page_retry_interval = 0

        transient_error = requests.HTTPError("500 Server Error")
        adapter.fetch_page = Mock(side_effect=[
            self.soup(self.html(
                image="/attachments/first.jpg",
                next_href="/threads/example.1/page-2",
            )),
            transient_error,
            self.soup(self.html(
                image="/attachments/second.jpg",
                next_href=None,
            )),
        ])

        result = adapter.resolve_thread("https://simpcity.cr/threads/example.1/")

        self.assertEqual(len(result["media"]), 2)
        self.assertEqual(
            [item["media_url"] for item in result["media"]],
            [
                "https://simpcity.cr/attachments/first.jpg",
                "https://simpcity.cr/attachments/second.jpg",
            ],
        )

    def test_extracts_video_src_elements(self):
        adapter = self.make_adapter()
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <video src="/attachments/video.mp4"></video>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["media_url"], "https://simpcity.cr/attachments/video.mp4")
        self.assertEqual(result[0]["filename"], "video.mp4")

    def test_video_only_extraction_skips_images_and_keeps_videos(self):
        adapter = self.make_adapter()
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <img class="bbImage" src="/attachments/image.jpg" />
                <video src="/attachments/video.mp4"></video>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
            download_images=False,
            download_videos=True,
        )

        self.assertEqual([item["filename"] for item in result], ["video.mp4"])

    def test_extracts_linked_video_files_from_post_content(self):
        adapter = self.make_adapter()
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <a href="https://cdn.example.test/file.webm">watch</a>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["media_url"], "https://cdn.example.test/file.webm")
        self.assertEqual(result[0]["filename"], "file.webm")

    def test_expands_bunkr_links_from_post_content(self):
        adapter = self.make_adapter()
        adapter.bunkr_adapter.resolve_url.return_value = {
            "folder_name": "bunkr_album",
            "media": [
                {
                    "media_url": "https://cdn.bunkr.test/file.mp4",
                    "filename": "file.mp4",
                    "post_id": None,
                    "title": "bunkr_album",
                    "published": "",
                }
            ],
        }
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <a href="https://bunkr.cr/a/example">bunkr album</a>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["media_url"], "https://cdn.bunkr.test/file.mp4")
        self.assertEqual(result[0]["filename"], "file.mp4")
        adapter.bunkr_adapter.resolve_url.assert_called_once_with("https://bunkr.cr/a/example")

    def test_expands_bunkr_links_from_attachment_blocks(self):
        adapter = self.make_adapter()
        adapter.bunkr_adapter.resolve_url.return_value = {
            "folder_name": "bunkr_file",
            "media": [{"media_url": "https://cdn.bunkr.test/file.jpg", "filename": "file.jpg"}],
        }
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <section class="message-attachments">
                  <a href="https://bunkr.cr/f/example">bunkr file</a>
                </section>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["media_url"], "https://cdn.bunkr.test/file.jpg")
        adapter.bunkr_adapter.resolve_url.assert_called_once_with("https://bunkr.cr/f/example")

    def test_expands_supported_file_host_links_from_post_content(self):
        adapter = self.make_adapter()
        adapter.file_host_adapters = {
            "pixeldrain": Mock(resolve_url=Mock(return_value={"folder_name": "pd", "media": [{"media_url": "https://pixeldrain.com/api/file/a?download", "filename": "a.mp4"}]})),
            "turbovid": Mock(resolve_url=Mock(return_value={"folder_name": "tv", "media": [{"media_url": "https://dl7.turbocdn.st/data/t/t.mp4?token=1", "filename": "t.mp4"}]})),
            "gofile": Mock(resolve_url=Mock(return_value={"folder_name": "gf", "media": [{"media_url": "https://store.gofile.io/download/web/b/b.mp4", "filename": "b.mp4"}]})),
            "jpg5": Mock(resolve_url=Mock(return_value={"folder_name": "jpg", "media": [{"media_url": "https://simp6.cuckcapital.cr/images3/c.jpg", "filename": "c.jpg"}]})),
        }
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <a href="https://pixeldrain.com/u/a">pd</a>
                <a href="https://turbo.cr/v/t">tv</a>
                <a href="https://gofile.io/d/b">gf</a>
                <a href="https://jpg6.su/img/c">jpg</a>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
        )

        self.assertEqual([item["filename"] for item in result], ["a.mp4", "t.mp4", "b.mp4", "c.jpg"])

    def test_video_only_skips_image_only_jpg_host_resolution(self):
        adapter = self.make_adapter()
        adapter.file_host_adapters = {
            "turbovid": Mock(resolve_url=Mock(return_value={"folder_name": "tv", "media": [{"media_url": "https://dl7.turbocdn.st/data/t.mp4", "filename": "t.mp4"}]})),
            "jpg5": Mock(resolve_url=Mock(return_value={"folder_name": "jpg", "media": [{"media_url": "https://simp6.cuckcapital.cr/images3/c.jpg", "filename": "c.jpg"}]})),
        }
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <a href="https://turbo.cr/v/t">tv</a>
                <a href="https://jpg6.su/img/c">jpg</a>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
            download_images=False,
            download_videos=True,
        )

        self.assertEqual([item["filename"] for item in result], ["t.mp4"])
        adapter.file_host_adapters["turbovid"].resolve_url.assert_called_once_with("https://turbo.cr/v/t")
        adapter.file_host_adapters["jpg5"].resolve_url.assert_not_called()

    def test_detects_direct_turbocdn_video_links_with_query_string(self):
        adapter = self.make_adapter()
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <a href="https://dl7.turbocdn.st/data/oDzrfx3XUQNMZ.mp4?exp=1&token=abc">turbo cdn</a>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["media_url"], "https://dl7.turbocdn.st/data/oDzrfx3XUQNMZ.mp4?exp=1&token=abc")
        self.assertEqual(result[0]["filename"], "oDzrfx3XUQNMZ.mp4")

    def test_expands_turbo_embed_src_links_from_post_content(self):
        adapter = self.make_adapter()
        adapter.file_host_adapters = {
            "turbovid": Mock(resolve_url=Mock(return_value={"folder_name": "tv", "media": [{"media_url": "https://dl7.turbocdn.st/data/embed.mp4", "filename": "embed.mp4"}]})),
        }
        soup = self.soup("""
        <html>
          <body>
            <div class="message-main">
              <div class="message-userContent">
                <iframe src="https://turbo.cr/embed/Tb0sGMx4jhuPf"></iframe>
              </div>
            </div>
          </body>
        </html>
        """)

        result = adapter._extract_page_media(
            soup,
            base_url="https://simpcity.cr/threads/example.1/",
            folder_name="Thread Title",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["media_url"], "https://dl7.turbocdn.st/data/embed.mp4")
        adapter.file_host_adapters["turbovid"].resolve_url.assert_called_once_with("https://turbo.cr/embed/Tb0sGMx4jhuPf")
