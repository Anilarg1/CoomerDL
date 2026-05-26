from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DownloadJob:
    media_url: str
    target_folder: Path
    filename: str
    domain: str
    headers: dict[str, str] = field(default_factory=dict)
    user_id: str | None = None
    post_id: str | None = None
    post_name: str | None = None
    post_time: str | None = None
    media_type: str = "other"
    database_key: str | None = None

    def __post_init__(self):
        if self.database_key is None:
            object.__setattr__(self, "database_key", self.media_url)

    @property
    def final_path(self) -> Path:
        return self.target_folder / self.filename

    @property
    def temp_path(self) -> Path:
        return self.target_folder / f"{self.filename}.tmp"
