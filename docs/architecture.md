# SimpCity Scraper Architecture

SimpCity Scraper uses a PySide UI backed by a site registry and shared download engine.

## Flow

1. The UI builds a `DownloadRequest`.
2. `MainController` asks `SiteRegistry` to parse and classify the URL.
3. The selected site downloader fetches page or API metadata.
4. The site planner or downloader converts metadata into `DownloadJob` objects.
5. `DownloadEngine` downloads each job, using temp files, resume headers, retry settings, SQLite history, and progress callbacks.

File hosts are implemented as adapters that resolve host-specific pages or APIs into normalized media entries. `FileHostDownloader` then turns those entries into shared `DownloadJob` objects so PixelDrain, TurboVid, Filester, GoFile, and JPG6/JPG5 reuse common retry, history, progress, filtering, streaming, and file-signature extension correction behavior.

## Key Files

- `app/services/site_registry.py`: URL-to-site matching.
- `downloader/models/download_job.py`: normalized download job model.
- `downloader/engine/download_engine.py`: shared file transfer engine.
- `downloader/engine/download_history.py`: SQLite download history.
- `downloader/file_host.py`: generic file-host downloader wrapper.
- `downloader/adapters/*_adapter.py`: host-specific metadata resolvers.
- `downloader/planners/coomer_kemono_planner.py`: Coomer/Kemono post-to-job conversion.
