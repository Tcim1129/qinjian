from app.core.config import Settings


def test_cors_allowed_origins_include_null_for_local_web():
    settings = Settings(
        FRONTEND_ORIGIN="http://localhost:5173",
    )

    assert settings.cors_allowed_origins() == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "null",
    ]


def test_cors_allowed_origins_skip_null_for_non_local_web():
    settings = Settings(
        FRONTEND_ORIGIN="https://qinjian.example.com",
    )

    assert settings.cors_allowed_origins() == ["https://qinjian.example.com"]


def test_cors_allowed_origins_mirror_127001_to_localhost():
    settings = Settings(
        FRONTEND_ORIGIN="http://127.0.0.1:3000",
    )

    assert settings.cors_allowed_origins() == [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "null",
    ]
