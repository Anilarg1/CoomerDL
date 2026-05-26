from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".wmv", ".m4v"}
COMPRESSED_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}


def media_type_for_url(media_url: str) -> str:
    extension = Path(media_url.split("?", 1)[0]).suffix.lower()
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in COMPRESSED_EXTENSIONS:
        return "compressed"
    if extension in DOCUMENT_EXTENSIONS:
        return "document"
    return "other"


def should_download_media(
    media_url: str,
    download_images: bool = True,
    download_videos: bool = True,
    download_compressed: bool = True,
    download_documents: bool = True,
    download_other: bool = True,
) -> bool:
    media_type = media_type_for_url(media_url)
    return {
        "image": download_images,
        "video": download_videos,
        "compressed": download_compressed,
        "document": download_documents,
        "other": download_other,
    }[media_type]
