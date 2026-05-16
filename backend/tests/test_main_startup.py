from app.core.config import settings
from app.main import _should_auto_create_tables


def test_auto_create_tables_defaults_to_disabled():
    original = settings.AUTO_CREATE_TABLES
    settings.AUTO_CREATE_TABLES = False
    try:
        assert _should_auto_create_tables() is False
    finally:
        settings.AUTO_CREATE_TABLES = original


def test_auto_create_tables_can_be_enabled_explicitly():
    original = settings.AUTO_CREATE_TABLES
    settings.AUTO_CREATE_TABLES = True
    try:
        assert _should_auto_create_tables() is True
    finally:
        settings.AUTO_CREATE_TABLES = original
