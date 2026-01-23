import os
from urllib.parse import quote_plus

from app.db.progress_sql import build_aws_database_url


def test_build_aws_database_url_happy_path(monkeypatch):
    # Ensure no global DATABASE_URL interferes
    monkeypatch.delenv("DATABASE_URL", raising=False)

    monkeypatch.setenv("AWS_DB_HOST", "db.example.amazonaws.com")
    monkeypatch.setenv("AWS_DB_NAME", "mydb")
    monkeypatch.setenv("AWS_DB_USER", "user")
    monkeypatch.setenv("AWS_DB_PASSWORD", "p@ss:word")
    monkeypatch.setenv("AWS_DB_PORT", "5433")

    url = build_aws_database_url()

    user_enc = quote_plus("user")
    pwd_enc = quote_plus("p@ss:word")
    expected = f"postgresql+asyncpg://{user_enc}:{pwd_enc}@db.example.amazonaws.com:5433/mydb"
    assert url == expected


def test_build_aws_database_url_missing_returns_none(monkeypatch):
    # Remove any AWS_* vars
    monkeypatch.delenv("AWS_DB_HOST", raising=False)
    monkeypatch.delenv("AWS_DB_NAME", raising=False)
    monkeypatch.delenv("AWS_DB_USER", raising=False)
    monkeypatch.delenv("AWS_DB_PASSWORD", raising=False)

    assert build_aws_database_url() is None


def test_build_aws_database_url_ssl(monkeypatch):
    monkeypatch.setenv("AWS_DB_HOST", "host")
    monkeypatch.setenv("AWS_DB_NAME", "db")
    monkeypatch.setenv("AWS_DB_USER", "u")
    monkeypatch.setenv("AWS_DB_PASSWORD", "p")
    monkeypatch.setenv("AWS_REQUIRE_SSL", "true")

    url = build_aws_database_url()

    assert url is not None
    assert url.endswith("?sslmode=require")
