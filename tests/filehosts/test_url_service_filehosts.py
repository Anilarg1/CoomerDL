from app.services.site_registry import build_default_site_registry
from app.services.url_service import UrlService


def site_type(url):
    return UrlService().parse_download_url(url).site_type


def test_parses_file_host_urls():
    assert site_type("https://pixeldrain.com/u/abc123") == "pixeldrain"
    assert site_type("https://turbo.cr/v/abc123") == "turbovid"
    assert site_type("https://gofile.io/d/abc123") == "gofile"
    assert site_type("https://filester.si/d/fileSlug") == "filester"
    assert site_type("https://filester.gg/d/fileSlug") == "filester"
    assert site_type("https://jpg6.su/img/img-7641.No98SXI") == "jpg5"
    assert site_type("https://jpg5.su/img/example") == "jpg5"


def test_registry_matches_file_hosts():
    registry = build_default_site_registry()

    assert registry.match("https://pixeldrain.com/u/abc123").handler.site_type == "pixeldrain"
    assert registry.match("https://turbovid.cr/v/abc123").handler.site_type == "turbovid"
    assert registry.match("https://gofile.io/d/abc123").handler.site_type == "gofile"
    assert registry.match("https://filester.gg/d/fileSlug").handler.site_type == "filester"
    assert registry.match("https://jpg6.su/img/img-7641.No98SXI").handler.site_type == "jpg5"
