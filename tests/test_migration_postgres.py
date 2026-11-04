import json
import os
import sqlite3
import sys
from types import SimpleNamespace

import psycopg
import pytest

from scripts import migrate_sqlite_to_rds as migration


pytestmark = pytest.mark.skipif(
    os.environ.get("CLOUDOPS_MIGRATION_TEST") != "1",
    reason="Requires the disposable local PostgreSQL container",
)

TEST_DSN = (
    "host=127.0.0.1 port=5434 dbname=migration_test "
    "user=migration_test password=local-test-only connect_timeout=5"
)


@pytest.fixture
def laboratory(tmp_path, monkeypatch):
    real_connect = psycopg.connect

    def connect():
        return real_connect(TEST_DSN)

    with connect() as connection:
        assert connection.execute(
            "SELECT current_database()"
        ).fetchone()[0] == "migration_test"
        connection.execute("DROP TABLE IF EXISTS public.ticket")
        connection.execute("""
            CREATE TABLE public.ticket (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                status VARCHAR(20) NOT NULL
            )
        """)

    source = tmp_path / "tickets.db"
    rows = [
        (1, "First", "Original description", "open"),
        (2, "Second", "Punctuation: ' & é", "closed"),
    ]
    with sqlite3.connect(source) as connection:
        connection.execute("""
            CREATE TABLE ticket (
                id INTEGER PRIMARY KEY,
                title TEXT,
                description TEXT,
                status TEXT
            )
        """)
        connection.executemany(
            "INSERT INTO ticket VALUES (?, ?, ?, ?)", rows
        )

    def secret_client(service, **kwargs):
        assert service == "secretsmanager"
        return SimpleNamespace(
            get_secret_value=lambda **kwargs: {
                "SecretString": json.dumps({
                    "username": "migration_test",
                    "password": "local-test-only",
                })
            }
        )

    monkeypatch.setitem(
        sys.modules, "boto3", SimpleNamespace(client=secret_client)
    )

    def local_connection(**kwargs):
        assert kwargs["sslmode"] == "verify-full"
        return connect()

    monkeypatch.setattr(psycopg, "connect", local_connection)

    def run(apply=False):
        arguments = [
            "migration",
            "--sqlite", str(source),
            "--host", "unused-local-test",
            "--admin-secret-arn", "unused-local-test",
        ]
        if apply:
            arguments.append("--apply")
        monkeypatch.setattr(sys, "argv", arguments)
        migration.main()

    return connect, run, rows


def test_preflight_does_not_insert(laboratory):
    connect, run, _ = laboratory
    run()

    with connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM ticket"
        ).fetchone()[0] == 0


def test_copy_rerun_and_next_generated_id(laboratory):
    connect, run, rows = laboratory
    run(apply=True)
    run(apply=True)

    with connect() as connection:
        assert connection.execute(
            "SELECT id, title, description, status FROM ticket ORDER BY id"
        ).fetchall() == rows
        new_id = connection.execute("""
            INSERT INTO ticket (title, description, status)
            VALUES ('New ticket', '', 'open') RETURNING id
        """).fetchone()[0]
        assert new_id == 3


def test_conflict_is_rejected_without_copying(laboratory):
    connect, run, _ = laboratory
    with connect() as connection:
        connection.execute("""
            INSERT INTO ticket VALUES (2, 'Conflicting title', '', 'open')
        """)

    with pytest.raises(ValueError, match="conflicting ticket"):
        run(apply=True)

    with connect() as connection:
        assert connection.execute(
            "SELECT id, title FROM ticket"
        ).fetchall() == [(2, "Conflicting title")]


def test_extra_target_ticket_is_rejected(laboratory):
    connect, run, _ = laboratory
    with connect() as connection:
        connection.execute("""
            INSERT INTO ticket VALUES (99, 'Target only', '', 'open')
        """)

    with pytest.raises(ValueError, match="conflicting ticket"):
        run(apply=True)

    with connect() as connection:
        assert connection.execute(
            "SELECT id FROM ticket"
        ).fetchall() == [(99,)]
