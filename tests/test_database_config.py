import pytest

from app import create_app


def test_database_url_from_file(tmp_path, monkeypatch):
    secret_file = tmp_path / "database-url"
    secret_file.write_text("sqlite:///:memory:\n")

    monkeypatch.setenv("DATABASE_URL_FILE", str(secret_file))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///should-not-be-used.db")

    app = create_app()

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_missing_database_url_file_stops_startup(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL_FILE", str(tmp_path / "missing")
    )

    with pytest.raises(FileNotFoundError):
        create_app()


def test_empty_database_url_file_stops_startup(tmp_path, monkeypatch):
    secret_file = tmp_path / "database-url"
    secret_file.write_text("\n")

    monkeypatch.setenv("DATABASE_URL_FILE", str(secret_file))

    with pytest.raises(RuntimeError, match="Database URL file is empty"):
        create_app()
