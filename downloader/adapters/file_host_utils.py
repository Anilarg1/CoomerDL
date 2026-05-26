import re
from urllib.parse import urlparse


VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".wmv", ".flv", ".ts"}
VIDEO_MIME_PREFIXES = ("video/",)


def clean_filename(value, fallback="file"):
    cleaned = re.sub(r'[<>:"/\\|?*\u200b]', "_", str(value or "")).strip()
    return cleaned or fallback


def origin_from_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def looks_like_video(filename="", mime_type=""):
    suffix = "." + str(filename or "").rsplit(".", 1)[-1].lower() if "." in str(filename or "") else ""
    mime = str(mime_type or "").lower()
    return suffix in VIDEO_EXTENSIONS or any(mime.startswith(prefix) for prefix in VIDEO_MIME_PREFIXES)
