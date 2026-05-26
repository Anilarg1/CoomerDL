import json

import pytest

from app.services.cookies_settings_service import CookiesSettingsService


class FakeCookie:
    def __init__(self, name, value, domain, path="/", secure=True, expires=None):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.secure = secure
        self.expires = expires


def test_import_browser_cookies_requests_only_simpcity_domain(tmp_path):
    calls = []

    def fake_loader(domain_name=None):
        calls.append(domain_name)
        return [FakeCookie("xf_user", "secret", ".simpcity.cr")]

    service = CookiesSettingsService(tmp_path / "simpcity.json")

    cookies = service.import_simpcity_cookies_from_browser(loader=fake_loader)

    assert calls == ["simpcity.cr"]
    assert cookies == [
        {
            "name": "xf_user",
            "value": "secret",
            "domain": ".simpcity.cr",
            "path": "/",
            "secure": True,
            "expires": None,
        }
    ]
    assert json.loads((tmp_path / "simpcity.json").read_text(encoding="utf-8")) == cookies


def test_import_browser_cookies_filters_non_simpcity_domains(tmp_path):
    def fake_loader(domain_name=None):
        return [
            FakeCookie("xf_user", "secret", ".simpcity.cr"),
            FakeCookie("session", "do-not-save", ".example.com"),
        ]

    service = CookiesSettingsService(tmp_path / "simpcity.json")

    cookies = service.import_simpcity_cookies_from_browser(loader=fake_loader)

    assert [cookie["domain"] for cookie in cookies] == [".simpcity.cr"]
    assert "do-not-save" not in (tmp_path / "simpcity.json").read_text(encoding="utf-8")


def test_import_browser_cookies_errors_when_no_simpcity_cookies_found(tmp_path):
    service = CookiesSettingsService(tmp_path / "simpcity.json")

    with pytest.raises(ValueError, match="No SimpCity cookies"):
        service.import_simpcity_cookies_from_browser(loader=lambda domain_name=None: [])


def test_import_browser_cookies_tries_next_browser_when_one_loader_crashes(tmp_path):
    calls = []

    def broken_loader(domain_name=None):
        calls.append(("broken", domain_name))
        raise TypeError("Arc path probe failed")

    def working_loader(domain_name=None):
        calls.append(("working", domain_name))
        return [FakeCookie("xf_user", "secret", ".simpcity.cr")]

    service = CookiesSettingsService(tmp_path / "simpcity.json")

    cookies = service.import_simpcity_cookies_from_browser(browser_loaders=[broken_loader, working_loader])

    assert calls == [("broken", "simpcity.cr"), ("working", "simpcity.cr")]
    assert [cookie["name"] for cookie in cookies] == ["xf_user"]


def test_import_browser_cookies_tries_next_browser_when_first_has_no_simpcity_cookies(tmp_path):
    calls = []

    def empty_browser_loader(domain_name=None):
        calls.append(("empty", domain_name))
        return [FakeCookie("session", "do-not-save", ".example.com")]

    def simpcity_browser_loader(domain_name=None):
        calls.append(("simpcity", domain_name))
        return [FakeCookie("xf_user", "secret", ".simpcity.cr")]

    service = CookiesSettingsService(tmp_path / "simpcity.json")

    cookies = service.import_simpcity_cookies_from_browser(
        browser_loaders=[empty_browser_loader, simpcity_browser_loader]
    )

    assert calls == [("empty", "simpcity.cr"), ("simpcity", "simpcity.cr")]
    assert [cookie["domain"] for cookie in cookies] == [".simpcity.cr"]
    assert "do-not-save" not in (tmp_path / "simpcity.json").read_text(encoding="utf-8")
