from concurrent.futures import as_completed

from downloader.core.base_api_downloader import BaseApiDownloader
from downloader.adapters.bunkr_adapter import BunkrAdapter


class BunkrDownloader(BaseApiDownloader):
    def __init__(self, *args, translations=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.translations = translations or {}
        self.adapter = BunkrAdapter(
            session=self.session,
            headers=self.headers,
            log_callback=self.log_callback,
            tr=self._translate_message,
        )
        self.domain_name = "bunkr"

    def _translate_message(self, key, **kwargs):
        if callable(self.tr):
            try:
                return self.tr(key, **kwargs)
            except TypeError:
                text = self.tr(key)
                if kwargs:
                    try:
                        return text.format(**kwargs)
                    except Exception:
                        return text
                return text

        text = self.translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def descargar_post_bunkr(self, url_post):
        try:
            self.log("BUNKR_STARTING_POST_DOWNLOAD", url=url_post)

            resolved = self.adapter.resolve_url(url_post)
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
                    break
                future.result()

        except Exception as e:
            self.log("BUNKR_ERROR_PROCESSING_POST", url=url_post, error=e)
        finally:
            self.shutdown_executor()

    def descargar_perfil_bunkr(self, url_perfil):
        try:
            self.log("BUNKR_STARTING_PROFILE_DOWNLOAD", url=url_perfil)

            resolved = self.adapter.resolve_url(url_perfil)
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
                    break
                future.result()

        except Exception as e:
            self.log("BUNKR_ERROR_PROCESSING_PROFILE", url=url_perfil, error=e)
        finally:
            self.shutdown_executor()

    def set_max_downloads(self, max_downloads):
        self.update_max_downloads(max_downloads)
