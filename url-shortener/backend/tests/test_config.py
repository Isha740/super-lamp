from app.config import Settings


def test_postgres_urls_get_driver_prefix():
    assert Settings(database_url="postgres://u:p@h/db").database_url == "postgresql+psycopg2://u:p@h/db"
    got = Settings(database_url="postgresql://u:p@h/db?sslmode=require").database_url
    assert got == "postgresql+psycopg2://u:p@h/db?sslmode=require"


def test_explicit_driver_and_sqlite_untouched():
    assert Settings(database_url="postgresql+psycopg2://u:p@h/db").database_url == "postgresql+psycopg2://u:p@h/db"
    assert Settings(database_url="sqlite:///x.db").database_url == "sqlite:///x.db"
