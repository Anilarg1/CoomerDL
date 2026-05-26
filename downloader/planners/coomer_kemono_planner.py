import os
from pathlib import Path
from urllib.parse import urljoin

from downloader.engine.download_filters import media_type_for_url, should_download_media
from downloader.models.download_job import DownloadJob


class CoomerKemonoPlanner:
    def __init__(
        self,
        download_folder: Path,
        site: str,
        service: str,
        user_id: str,
        headers: dict[str, str] | None = None,
        folder_structure: str = "default",
        download_images: bool = True,
        download_videos: bool = True,
        download_compressed: bool = True,
        filename_resolver=None,
        folder_resolver=None,
    ):
        self.download_folder = Path(download_folder)
        self.site = site
        self.service = service
        self.user_id = user_id
        self.headers = headers or {}
        self.folder_structure = folder_structure
        self.download_images = download_images
        self.download_videos = download_videos
        self.download_compressed = download_compressed
        self.filename_resolver = filename_resolver
        self.folder_resolver = folder_resolver

    @property
    def domain(self) -> str:
        return "kemono" if "kemono" in self.site else "coomer"

    def _full_url(self, path: str | None) -> str | None:
        if not path:
            return None
        return urljoin(f"https://{self.site}/", path if str(path).startswith("/") else f"/{path}")

    def _entries_for_post(self, post: dict):
        file_entry = post.get("file") or {}
        main_url = self._full_url(file_entry.get("path") or file_entry.get("url") or file_entry.get("name"))
        if main_url:
            yield main_url

        for attachment in post.get("attachments") or []:
            attachment_url = self._full_url(
                attachment.get("path") or attachment.get("url") or attachment.get("name")
            )
            if attachment_url:
                yield attachment_url

    def _target_folder(self, media_url: str, post_id: str):
        extension = os.path.splitext(media_url.split("?", 1)[0])[1].lower()
        if self.folder_resolver:
            return Path(self.folder_resolver(extension, self.user_id, post_id))

        media_type = media_type_for_url(media_url)
        folder_name = {
            "image": "images",
            "video": "videos",
            "compressed": "compressed",
            "document": "documents",
            "other": "other",
        }[media_type]

        if self.folder_structure == "post_number" and post_id:
            return self.download_folder / self.user_id / f"post_{post_id}" / folder_name
        return self.download_folder / self.user_id / folder_name

    def create_jobs(self, posts: list[dict]) -> list[DownloadJob]:
        jobs = []
        seen = set()

        for post in posts:
            post_id = post.get("id") or "unknown_id"
            post_name = post.get("title") or ""
            post_time = post.get("published") or ""
            attachment_index = 0

            for media_url in self._entries_for_post(post):
                if media_url in seen:
                    continue
                seen.add(media_url)

                if not should_download_media(
                    media_url,
                    download_images=self.download_images,
                    download_videos=self.download_videos,
                    download_compressed=self.download_compressed,
                ):
                    continue

                attachment_index += 1
                filename = (
                    self.filename_resolver(
                        media_url,
                        post_id=post_id,
                        post_name=post_name,
                        attachment_index=attachment_index,
                        post_time=post_time,
                    )
                    if self.filename_resolver
                    else os.path.basename(media_url.split("?", 1)[0])
                )

                jobs.append(
                    DownloadJob(
                        media_url=media_url,
                        target_folder=self._target_folder(media_url, post_id),
                        filename=filename,
                        domain=self.domain,
                        headers=dict(self.headers),
                        user_id=self.user_id,
                        post_id=post_id,
                        post_name=post_name,
                        post_time=post_time,
                        media_type=media_type_for_url(media_url),
                    )
                )

        return jobs
