from dataclasses import dataclass
from typing import Callable

from app.services.url_service import ParsedDownloadUrl


UrlMatcher = Callable[[str], ParsedDownloadUrl | None]


@dataclass(frozen=True)
class SiteHandler:
    site_type: str
    matcher: UrlMatcher
