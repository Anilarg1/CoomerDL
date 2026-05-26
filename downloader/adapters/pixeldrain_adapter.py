from urllib.parse import urlparse

import requests

from downloader.adapters.file_host_utils import clean_filename, origin_from_url


class PixelDrainAdapter:
    site_name = "pixeldrain"

    def __init__(self, session=None, log_callback=None, tr=None):
        self.session = session or requests.Session()
        self.log_callback = log_callback
        self.tr = tr

    def resolve_url(self, url):
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parts[:1] == ["u"] and len(parts) >= 2:
            return self._resolve_file(url, parts[1])
        if parts[:2] == ["api", "file"] and len(parts) >= 3:
            return self._resolve_file(url, parts[2])
        if parts[:1] == ["l"] and len(parts) >= 2:
            return self._resolve_list(url, parts[1], parsed.fragment)
        if parts[:2] == ["api", "list"] and len(parts) >= 3:
            return self._resolve_list(url, parts[2], parsed.fragment)
        if parts[:1] == ["d"] or parts[:2] == ["api", "filesystem"]:
            return self._resolve_filesystem(url)
        raise ValueError(f"Unsupported PixelDrain URL: {url}")

    def _request_json(self, api_url):
        response = self.session.get(api_url, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is False:
            raise ValueError(payload.get("message") or "PixelDrain API error")
        return payload

    def _media_from_file(self, file_data, origin):
        file_id = file_data["id"]
        filename = clean_filename(file_data.get("name") or file_id)
        return {
            "media_url": f"{origin}/api/file/{file_id}?download",
            "filename": filename,
            "title": "pixeldrain",
            "post_id": file_id,
            "published": file_data.get("date_upload", ""),
            "mime_type": file_data.get("mime_type", ""),
            "checksum": file_data.get("hash_sha256", ""),
        }

    def _resolve_file(self, url, file_id):
        origin = origin_from_url(url)
        payload = self._request_json(f"{origin}/api/file/{file_id}/info")
        return {
            "folder_name": clean_filename(f"pixeldrain_{file_id}"),
            "media": [self._media_from_file(payload, origin)],
        }

    def _resolve_list(self, url, list_id, fragment=""):
        origin = origin_from_url(url)
        payload = self._request_json(f"{origin}/api/list/{list_id}")
        files = payload.get("files", [])
        if fragment.startswith("item="):
            index = int(fragment.removeprefix("item="))
            files = [files[index]]
        return {
            "folder_name": clean_filename(f"{payload.get('title') or 'pixeldrain'}_{list_id}"),
            "media": [self._media_from_file(file_data, origin) for file_data in files],
        }

    def _resolve_filesystem(self, url):
        origin = origin_from_url(url)
        parsed = urlparse(url)
        if parsed.path.startswith("/api/filesystem/"):
            path = parsed.path.removeprefix("/api/filesystem/")
        else:
            path = parsed.path.removeprefix("/d/")
        payload = self._request_json(f"{origin}/api/filesystem/{path}?stat")
        children = payload.get("children", [])
        if not children and payload.get("path"):
            base_index = payload.get("base_index", len(payload["path"]) - 1)
            children = [payload["path"][base_index]]
        media = []
        for node in children:
            if node.get("type") != "file":
                continue
            node_path = node.get("path", "").lstrip("/")
            media.append({
                "media_url": f"{origin}/api/filesystem/{node_path}?attach",
                "filename": clean_filename(node.get("name") or node.get("id") or "pixeldrain_file"),
                "title": "pixeldrain",
                "post_id": node.get("id"),
                "published": node.get("modified", ""),
                "mime_type": node.get("file_type", ""),
                "checksum": node.get("sha256_sum", ""),
            })
        folder_id = path.strip("/").split("/", 1)[0] or "filesystem"
        return {"folder_name": clean_filename(f"pixeldrain_{folder_id}"), "media": media}
