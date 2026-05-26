# File Host Support Progress

Date: 2026-05-26

## Implemented

- Added `FileHostDownloader`, a generic wrapper over `BaseApiDownloader` and `DownloadEngine`.
- Added adapters for PixelDrain, TurboVid, GoFile, and Filester.
- Extended JPG5 support to recognize JPG6/JPG7/Cuckcapital-style URLs and single media pages.
- Wired PixelDrain, TurboVid, GoFile, and Filester into URL parsing, site registry, downloader factory, and main controller routing.
- Extended SimpCity embedded-link expansion for PixelDrain, TurboVid, GoFile, Filester, and JPG5/JPG6 links.
- Extended SimpCity video discovery to resolve Turbo iframe/embed `src` URLs and direct TurboCDN video links.
- Added duplicate filename protection for download jobs so case-only collisions such as `FullSizeRender.MOV` and `FullSizeRender.mov` save as distinct files on Windows.
- Added focused tests under `tests/filehosts`; run with `python -m pytest tests/filehosts`.

## Validation

- Unit tests mock host responses for PixelDrain, TurboVid, GoFile, Filester, JPG6/JPG5, and the generic downloader.
- Integration test uses a local fixture server to resolve a PixelDrain-shaped URL and stream a small MP4 payload through `DownloadEngine`.
- The local fixture validation confirms a completed file exists, has a `.mp4` extension, has nonzero size, and can be checksummed.
- SimpCity page 48 was resolved from the explicit approved URL and returned three Turbo embed videos. All three downloaded to completion with nonzero size, recognized video extensions, MP4 `ftyp` signatures, and SHA-256 checksums.

## Supported Hosts

- PixelDrain: `/u/<id>`, `/api/file/<id>`, `/l/<id>`, `/api/list/<id>`, and simple filesystem file entries.
- TurboVid: `/v/<id>`, `/d/<id>`, `/embed/<id>`, `/data/<id>.mp4`, albums, and simple library search pages.
- GoFile: `/d/<content_id>` folders/files and direct `/download/...` links; password query parameter is hashed for folder API requests.
- Filester: `/d/<slug>` files and basic `/f/<slug>` folder pages.
- JPG6/JPG5: single `/img/...` pages, gallery pages through existing JPG5 flow, and direct CDN image/video links.
- SimpCity expansion: direct video links, PixelDrain/Bunkr/Turbo page links, direct TurboCDN URLs, and Turbo iframe/embed URLs from the explicit page being processed.

## Blocked Or Limited

- Broad crawling is intentionally not added; only explicit URLs are fetched.
- GoFile private/password-protected folders still depend on API access and a correct `?password=...` value.
- Filester folder pagination and CDN fallback are minimal.
- PixelDrain recursive filesystem directory walking is limited to the returned file entries from the requested explicit URL.
- Cyberfile is not implemented because the requested scope replaces Cyberfile with JPG6 and JPG5.
