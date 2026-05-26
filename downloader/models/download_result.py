from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DownloadStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class DownloadResult:
    status: DownloadStatus
    media_url: str
    file_path: Path | None = None
    file_size: int = 0
    message: str = ""

    @classmethod
    def completed(cls, media_url: str, file_path: Path, file_size: int):
        return cls(DownloadStatus.COMPLETED, media_url, file_path, file_size, "completed")

    @classmethod
    def skipped(cls, media_url: str, message: str):
        return cls(DownloadStatus.SKIPPED, media_url, message=message)

    @classmethod
    def failed(cls, media_url: str, message: str):
        return cls(DownloadStatus.FAILED, media_url, message=message)

    @classmethod
    def cancelled(cls, media_url: str):
        return cls(DownloadStatus.CANCELLED, media_url, message="cancelled")
