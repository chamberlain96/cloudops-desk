import argparse
import json
import sqlite3
from pathlib import Path


def read_source(filename):
    path = Path(filename).resolve(strict=True)

    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as source:
        if source.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed")

        rows = source.execute(
            "SELECT id, title, description, status FROM ticket ORDER BY id"
        ).fetchall()

    for ticket_id, title, description, status in rows:
        if (
            not isinstance(ticket_id, int)
            or ticket_id < 1
            or not isinstance(title, str)
            or len(title) > 200
            or not isinstance(description, str)
            or not isinstance(status, str)
            or len(status) > 20
        ):
            raise ValueError("Source contains an incompatible ticket")

    return rows


def main():
    import boto3
    import psycopg

    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--admin-secret-arn", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    source_rows = read_source(args.sqlite)
    source_by_id = {row[0]: row for row in source_rows}

    client = boto3.client("secretsmanager", region_name="us-east-1")
    credentials = json.loads(
        client.get_secret_value(
            SecretId=args.admin_secret_arn
        )["SecretString"]
    )

    with psycopg.connect(
        host=args.host,
        port=5432,
        dbname="cloudops",
        user=credentials["username"],
        password=credentials["password"],
        sslmode="verify-full",
        sslrootcert="/opt/cloudops-desk/certs/us-east-1-bundle.pem",
        connect_timeout=5,
        options="-c statement_timeout=10000 -c lock_timeout=5000",
    ) as target:
        with target.cursor() as cursor:
            if args.apply:
                # Block concurrent table writes during copy and verification.
                cursor.execute(
                    "LOCK TABLE public.ticket IN ACCESS EXCLUSIVE MODE"
                )

            cursor.execute(
                "SELECT id, title, description, status "
                "FROM public.ticket ORDER BY id"
            )
            target_rows = cursor.fetchall()
            target_by_id = {row[0]: row for row in target_rows}

            for ticket_id, row in target_by_id.items():
                if source_by_id.get(ticket_id) != row:
                    raise ValueError(
                        "RDS contains an extra or conflicting ticket; "
                        "migration refused"
                    )

            missing = [
                row for row in source_rows if row[0] not in target_by_id
            ]

            if not args.apply:
                print(f"Source tickets: {len(source_rows)}")
                print(f"Matching RDS tickets: {len(target_rows)}")
                print(f"Tickets to copy: {len(missing)}")
                print("PASS: preflight only; no data changed")
                return

            cursor.executemany(
                "INSERT INTO public.ticket "
                "(id, title, description, status) VALUES (%s, %s, %s, %s)",
                missing,
            )

            cursor.execute(
                "SELECT id, title, description, status "
                "FROM public.ticket ORDER BY id"
            )
            if cursor.fetchall() != source_rows:
                raise ValueError("Copied data does not match SQLite")

            # Preserve a sequence already ahead of the migrated IDs.
            cursor.execute(
                "SELECT last_value, is_called FROM public.ticket_id_seq"
            )
            last_value, is_called = cursor.fetchone()
            highest_id = max(source_by_id, default=0)
            cursor.execute(
                "SELECT setval('public.ticket_id_seq', %s, %s)",
                (
                    max(last_value, highest_id),
                    is_called or highest_id >= last_value,
                ),
            )

    print(f"PASS: {len(source_rows)} tickets verified in RDS")
    print("PASS: ticket IDs and all field values preserved")
    print("PASS: ID sequence prepared for new tickets")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "FAIL: migration did not complete; "
            "credential and ticket details suppressed"
        ) from None
