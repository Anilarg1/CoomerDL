from app.services.site_registry import build_default_site_registry


def test_registry_matches_coomer_profile():
    registry = build_default_site_registry()

    match = registry.match("https://coomer.st/onlyfans/user/abc123")

    assert match is not None
    assert match.handler.site_type == "coomer_kemono"
    assert match.parsed.service == "onlyfans"
    assert match.parsed.user == "abc123"
    assert match.parsed.post is None


def test_registry_matches_coomer_post():
    registry = build_default_site_registry()

    match = registry.match("https://coomer.st/onlyfans/user/abc123/post/999")

    assert match is not None
    assert match.handler.site_type == "coomer_kemono"
    assert match.parsed.service == "onlyfans"
    assert match.parsed.user == "abc123"
    assert match.parsed.post == "999"
    assert match.parsed.is_post is True


def test_registry_matches_kemono_search_offset():
    registry = build_default_site_registry()

    match = registry.match("https://kemono.cr/patreon/user/abc123?q=test&o=50")

    assert match is not None
    assert match.handler.site_type == "coomer_kemono"
    assert match.parsed.query == "test"
    assert match.parsed.offset == 50


def test_registry_matches_bunkr_album():
    registry = build_default_site_registry()

    match = registry.match("https://bunkr.cr/a/example")

    assert match is not None
    assert match.handler.site_type == "bunkr"
    assert match.parsed.is_profile is True
    assert match.parsed.is_post is False


def test_registry_matches_bunkr_file_post():
    registry = build_default_site_registry()

    match = registry.match("https://bunkr.cr/f/example")

    assert match is not None
    assert match.handler.site_type == "bunkr"
    assert match.parsed.is_post is True


def test_registry_matches_erome_album():
    registry = build_default_site_registry()

    match = registry.match("https://www.erome.com/a/album-id")

    assert match is not None
    assert match.handler.site_type == "erome"
    assert match.parsed.is_album is True


def test_registry_matches_simpcity():
    registry = build_default_site_registry()

    match = registry.match("https://simpcity.cr/threads/example.123/")

    assert match is not None
    assert match.handler.site_type == "simpcity"


def test_registry_matches_jpg5():
    registry = build_default_site_registry()

    match = registry.match("https://jpg5.su/album/example")

    assert match is not None
    assert match.handler.site_type == "jpg5"


def test_registry_matches_coomerfans_post():
    registry = build_default_site_registry()

    match = registry.match("https://coomerfans.com/p/example")

    assert match is not None
    assert match.handler.site_type == "coomerfans"
    assert match.parsed.is_post is True


def test_registry_returns_none_for_unknown_url():
    registry = build_default_site_registry()

    match = registry.match("https://example.com/nope")

    assert match is None
