import argparse
import json
import secrets

import boto3
import psycopg
from psycopg import sql


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--admin-secret-arn", required=True)
    parser.add_argument("--app-secret-arn", required=True)
    args = parser.parse_args()

    client = boto3.client("secretsmanager", region_name="us-east-1")
    admin = json.loads(
        client.get_secret_value(
            SecretId=args.admin_secret_arn
        )["SecretString"]
    )

    # Reuse the saved password when rerunning this script.
    try:
        application = json.loads(
            client.get_secret_value(
                SecretId=args.app_secret_arn
            )["SecretString"]
        )
    except client.exceptions.ResourceNotFoundException:
        application = {
            "username": "cloudops_app",
            "password": secrets.token_urlsafe(32),
            "host": args.host,
            "port": 5432,
            "dbname": "cloudops",
        }
        client.put_secret_value(
            SecretId=args.app_secret_arn,
            SecretString=json.dumps(application),
        )

    if (
        application.get("username") != "cloudops_app"
        or not application.get("password")
        or application.get("host") != args.host
        or application.get("dbname") != "cloudops"
    ):
        raise RuntimeError("Application secret configuration is unexpected")

    connection_options = {
        "host": args.host,
        "port": 5432,
        "dbname": "cloudops",
        "sslmode": "verify-full",
        "sslrootcert": "/opt/cloudops-desk/certs/us-east-1-bundle.pem",
        "connect_timeout": 5,
        "options": "-c statement_timeout=5000",
    }

    with psycopg.connect(
        **connection_options,
        user=admin["username"],
        password=admin["password"],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s",
                ("cloudops_app",),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    "CREATE ROLE cloudops_app LOGIN "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOREPLICATION NOBYPASSRLS"
                )

            cursor.execute(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, "
                "rolreplication, rolbypassrls "
                "FROM pg_roles WHERE rolname = 'cloudops_app'"
            )
            if any(cursor.fetchone()):
                raise RuntimeError("Application role has elevated privileges")

            cursor.execute(
                "SELECT 1 FROM pg_auth_members "
                "WHERE member = "
                "(SELECT oid FROM pg_roles WHERE rolname = 'cloudops_app')"
            )
            if cursor.fetchone() is not None:
                raise RuntimeError("Application role has unexpected memberships")

            cursor.execute(
                sql.SQL("ALTER ROLE cloudops_app LOGIN PASSWORD {}").format(
                    sql.Literal(application["password"])
                )
            )
            cursor.execute("GRANT CONNECT ON DATABASE cloudops TO cloudops_app")
            cursor.execute("GRANT USAGE ON SCHEMA public TO cloudops_app")

    with psycopg.connect(
        **connection_options,
        user=application["username"],
        password=application["password"],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_user, ssl "
                "FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
            )
            if cursor.fetchone() != ("cloudops_app", True):
                raise RuntimeError("Application login or TLS verification failed")

    print("PASS: restricted application login works over verified TLS")
    print("PASS: credentials saved in Secrets Manager; password not displayed")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "FAIL: credential setup did not complete; secret values suppressed"
        ) from None
