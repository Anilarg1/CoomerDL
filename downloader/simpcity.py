from concurrent.futures import as_completed

from downloader.core.base_api_downloader import BaseApiDownloader
from downloader.adapters.simpcity_adapter import SimpCityAdapter


class SimpCity(BaseApiDownloader):
    def __init__(
        self,
        download_folder,
        max_workers=5,
        log_callback=None,
        enable_widgets_callback=None,
        update_progress_callback=None,
        update_global_progress_callback=None,
        max_retries=3,
        retry_interval=2.0,
        download_images=True,
        download_videos=True,
        download_engine="internal",
        external_downloader_path=None,
        tr=None,
    ):
        super().__init__(
            download_folder=download_folder,
            max_workers=max_workers,
            log_callback=log_callback,
            enable_widgets_callback=enable_widgets_callback,
            update_progress_callback=update_progress_callback,
            update_global_progress_callback=update_global_progress_callback,
            max_retries=max_retries,
            retry_interval=retry_interval,
            tr=tr,
            download_images=download_images,
            download_videos=download_videos,
            download_compressed=True,
            download_engine=download_engine,
            external_downloader_path=external_downloader_path,
        )

        self.adapter = SimpCityAdapter(
            log_callback=self.log_callback,
            tr=self.tr,
            page_max_retries=self.max_retries,
            page_retry_interval=self.retry_interval,
        )
        self.session = self.adapter.scraper
        self.domain_name = "simpcity"

    def download_images_from_simpcity(self, url, paginate=True, download_images=None, download_videos=None):
        try:
            self.log("SIMPCITY_PROCESSING_THREAD", url=url)

            if download_images is None:
                download_images = self.download_images
            if download_videos is None:
                download_videos = self.download_videos

            resolved = self.adapter.resolve_thread(
                url,
                paginate=paginate,
                download_images=download_images,
                download_videos=download_videos,
            )
            folder_name = resolved["folder_name"]
            media_entries = resolved["media"]

            jobs = self.create_download_jobs(folder_name, media_entries)
            self.total_files = len(jobs)
            self.completed_files = 0
            futures = []

            for job in jobs:
                if self.download_mode == "queue":
                    self.process_download_job(job)
                else:
                    future = self.executor.submit(self.process_download_job, job)
                    futures.append(future)

            self.futures = futures

            for future in as_completed(futures):
                if self.cancel_requested.is_set():
                    self.log("SIMPCITY_DOWNLOAD_CANCELLED")
                    break
                future.result()

            self.log("SIMPCITY_DOWNLOAD_COMPLETED")
        except Exception as e:
            self.log("SIMPCITY_ERROR_PROCESSING_THREAD", error=e)
        finally:
            self.shutdown_executor()
