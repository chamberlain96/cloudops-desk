import argparse
import json

import boto3
import psycopg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--admin-secret-arn", required=True)
    parser.add_argument("--app-secret-arn", required=True)
    args = parser.parse_args()

    client = boto3.client("secretsmanager", region_name="us-east-1")

    def read_secret(arn):
        response = client.get_secret_value(SecretId=arn)
        return json.loads(response["SecretString"])

    admin = read_secret(args.admin_secret_arn)
    application = read_secret(args.app_secret_arn)

    if application.get("username") != "cloudops_app":
        raise RuntimeError("Unexpected application username")

    options = {
        "host": args.host,
        "port": 5432,
        "dbname": "cloudops",
        "sslmode": "verify-full",
        "sslrootcert": "/opt/cloudops-desk/certs/us-east-1-bundle.pem",
        "connect_timeout": 5,
        "options": "-c statement_timeout=5000",
    }

    with psycopg.connect(
        **options,
        user=admin["username"],
        password=admin["password"],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS public.ticket (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL
                )
            """)

            cursor.execute(
                "GRANT CONNECT ON DATABASE cloudops TO cloudops_app"
            )
            cursor.execute(
                "GRANT USAGE ON SCHEMA public TO cloudops_app"
            )
            cursor.execute(
                "GRANT SELECT, INSERT ON TABLE public.ticket "
                "TO cloudops_app"
            )
            cursor.execute(
                "GRANT USAGE ON SEQUENCE public.ticket_id_seq "
                "TO cloudops_app"
            )

    with psycopg.connect(
        **options,
        user=application["username"],
        password=application["password"],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    has_table_privilege(
                        current_user, 'public.ticket', 'SELECT'
                    ),
                    has_table_privilege(
                        current_user, 'public.ticket', 'INSERT'
                    ),
                    has_sequence_privilege(
                        current_user, 'public.ticket_id_seq', 'USAGE'
                    ),
                    has_schema_privilege(
                        current_user, 'public', 'CREATE'
                    )
            """)
            permissions = cursor.fetchone()

            if permissions != (True, True, True, False):
                raise RuntimeError("Unexpected application permissions")

            cursor.execute(
                "SELECT id, title, description, status "
                "FROM public.ticket LIMIT 1"
            )

    print("PASS: ticket table prepared")
    print("PASS: application can SELECT and INSERT with sequence access")
    print("PASS: application cannot create tables in public schema")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "FAIL: schema setup or permission verification failed; "
            "secret values suppressed"
        ) from None
