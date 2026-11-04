import sqlite3

import pytest

from scripts.migrate_sqlite_to_rds import read_source


def create_source(path, rows):
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TABLE ticket (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        connection.executemany(
            "INSERT INTO ticket VALUES (?, ?, ?, ?)", rows
        )


def test_preserves_all_fields_and_orders_by_id(tmp_path):
    source = tmp_path / "tickets.db"
    rows = [
        (2, "Second ticket", "Keep punctuation: ' \" & é", "open"),
        (1, "First ticket", "", "closed"),
    ]
    create_source(source, rows)
    original_bytes = source.read_bytes()

    assert read_source(source) == sorted(rows)
    assert source.read_bytes() == original_bytes


def test_missing_source_is_not_created(tmp_path):
    source = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError):
        read_source(source)

    assert not source.exists()


def test_empty_ticket_table_is_supported(tmp_path):
    source = tmp_path / "tickets.db"
    create_source(source, [])

    assert read_source(source) == []


@pytest.mark.parametrize(
    "row",
    [
        (0, "Invalid ID", "", "open"),
        (1, "x" * 201, "", "open"),
        (1, "Invalid status", "", "x" * 21),
    ],
)
def test_rejects_incompatible_tickets(tmp_path, row):
    source = tmp_path / "tickets.db"
    create_source(source, [row])

    with pytest.raises(ValueError, match="incompatible ticket"):
        read_source(source)
