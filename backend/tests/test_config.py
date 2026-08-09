from app.config import Settings


def test_cors_origin_list_splits_and_trims():
    settings = Settings(cors_origins="https://a.example.com, https://b.example.com ,, ")
    assert settings.cors_origin_list == ["https://a.example.com", "https://b.example.com"]


def test_cors_origin_list_strips_trailing_slash():
    # Browsers send Origin with no trailing slash — a stray one in config would otherwise
    # silently break CORS matching. This was a real production bug.
    settings = Settings(cors_origins="https://ai.alliedsoftwareengineers.com/")
    assert settings.cors_origin_list == ["https://ai.alliedsoftwareengineers.com"]


def test_frontend_url_is_additive_to_cors_origins():
    settings = Settings(
        cors_origins="http://localhost:3000", frontend_url="https://ai.alliedsoftwareengineers.com"
    )
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "https://ai.alliedsoftwareengineers.com",
    ]


def test_frontend_url_alone_still_works_if_cors_origins_unset():
    settings = Settings(cors_origins="", frontend_url="https://ai.alliedsoftwareengineers.com")
    assert settings.cors_origin_list == ["https://ai.alliedsoftwareengineers.com"]


def test_duplicate_origins_are_deduped():
    settings = Settings(
        cors_origins="https://ai.alliedsoftwareengineers.com",
        frontend_url="https://ai.alliedsoftwareengineers.com/",
    )
    assert settings.cors_origin_list == ["https://ai.alliedsoftwareengineers.com"]
