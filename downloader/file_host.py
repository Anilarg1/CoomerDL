from concurrent.futures import as_completed

from downloader.core.base_api_downloader import BaseApiDownloader


class FileHostDownloader(BaseApiDownloader):
    def __init__(
        self,
        adapter,
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
        download_compressed=True,
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
            download_compressed=download_compressed,
            download_engine=download_engine,
            external_downloader_path=external_downloader_path,
        )
        self.adapter = adapter
        self.session = getattr(adapter, "session", self.session)
        self.domain_name = adapter.site_name

    def resolve_jobs(self, url):
        resolved = self.adapter.resolve_url(url)
        return self.create_download_jobs(
            resolved.get("folder_name") or self.domain_name,
            resolved.get("media", []),
            domain=self.domain_name,
        )

    def download_url(self, url):
        results = []
        try:
            self.log("FILE_HOST_PROCESSING_URL", url=url)
            jobs = self.resolve_jobs(url)
            self.total_files = len(jobs)
            self.completed_files = 0
            futures = []
            for job in jobs:
                if self.download_mode == "queue":
                    results.append(self.process_download_job(job))
                else:
                    futures.append(self.executor.submit(self.process_download_job, job))
            self.futures = futures
            for future in as_completed(futures):
                if self.cancel_requested.is_set():
                    self.log("FILE_HOST_DOWNLOAD_CANCELLED")
                    break
                results.append(future.result())
            self.log("FILE_HOST_DOWNLOAD_COMPLETED")
            return results
        except Exception as exc:
            self.log("FILE_HOST_ERROR_PROCESSING_URL", error=exc)
            raise
        finally:
            self.shutdown_executor()
