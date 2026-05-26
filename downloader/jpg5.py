from concurrent.futures import as_completed

from downloader.core.base_api_downloader import BaseApiDownloader
from downloader.adapters.jpg5_adapter import Jpg5Adapter


class Jpg5Downloader(BaseApiDownloader):
    def __init__(
        self,
        url,
        destination_folder,
        progress_manager,
        log_callback=None,
        tr=None,
        update_progress_callback=None,
        update_global_progress_callback=None,
        max_workers=3,
        download_engine="internal",
        external_downloader_path=None,
    ):
        super().__init__(
            download_folder=destination_folder,
            max_workers=max_workers,
            log_callback=log_callback,
            update_progress_callback=update_progress_callback,
            update_global_progress_callback=update_global_progress_callback,
            download_images=True,
            download_videos=False,
            download_compressed=False,
            tr=tr,
            download_engine=download_engine,
            external_downloader_path=external_downloader_path,
        )
        self.url = url
        self.progress_manager = progress_manager
        self.adapter = Jpg5Adapter(
            session=self.session,
            headers=self.headers,
            log_callback=self.log_callback,
            tr=self.tr,
        )
        self.domain_name = "jpg5"

    def download_jpg5_images(self):
        resolved = self.adapter.resolve_url(self.url)
        jobs = self.create_download_jobs(resolved.get("folder_name", ""), resolved["media"])

        self.total_files = len(jobs)
        self.completed_files = 0
        futures = []

        for job in jobs:
            if self.cancel_requested.is_set():
                self.log("JPG5_DOWNLOAD_CANCELLED_BY_USER")
                return

            if self.download_mode == "queue":
                self.process_download_job(job)
            else:
                future = self.executor.submit(self.process_download_job, job)
                futures.append(future)

        self.futures = futures

        for future in as_completed(futures):
            if self.cancel_requested.is_set():
                self.log("JPG5_DOWNLOAD_CANCELLED_BY_USER")
                break
            future.result()

        self.shutdown_executor()
