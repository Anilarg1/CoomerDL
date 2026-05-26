from dataclasses import dataclass

from app.models.site_handler import SiteHandler
from app.services.url_service import ParsedDownloadUrl, UrlService


@dataclass(frozen=True)
class SiteMatch:
    handler: SiteHandler
    parsed: ParsedDownloadUrl


class SiteRegistry:
    def __init__(self, handlers: list[SiteHandler]):
        self.handlers = handlers

    def match(self, raw_url: str) -> SiteMatch | None:
        for handler in self.handlers:
            parsed = handler.matcher(raw_url)
            if parsed is not None and parsed.site_type != "unknown":
                return SiteMatch(handler=handler, parsed=parsed)
        return None


def build_default_site_registry(url_service: UrlService | None = None) -> SiteRegistry:
    service = url_service or UrlService()

    def match_site(site_type: str):
        def matcher(raw_url: str) -> ParsedDownloadUrl | None:
            parsed = service.parse_download_url(raw_url)
            if parsed.site_type == site_type:
                return parsed
            return None

        return matcher

    return SiteRegistry(
        [
            SiteHandler("erome", match_site("erome")),
            SiteHandler("bunkr", match_site("bunkr")),
            SiteHandler("coomer_kemono", match_site("coomer_kemono")),
            SiteHandler("simpcity", match_site("simpcity")),
            SiteHandler("jpg5", match_site("jpg5")),
            SiteHandler("pixeldrain", match_site("pixeldrain")),
            SiteHandler("turbovid", match_site("turbovid")),
            SiteHandler("gofile", match_site("gofile")),
            SiteHandler("filester", match_site("filester")),
            SiteHandler("coomerfans", match_site("coomerfans")),
        ]
    )
