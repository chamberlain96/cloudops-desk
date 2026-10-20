import argparse
import json

import boto3
import psycopg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--secret-arn", required=True)
    args = parser.parse_args()

    client = boto3.client("secretsmanager", region_name="us-east-1")
    response = client.get_secret_value(SecretId=args.secret_arn)
    credentials = json.loads(response["SecretString"])

    with psycopg.connect(
        host=args.host,
        port=5432,
        dbname="cloudops",
        user=credentials["username"],
        password=credentials["password"],
        sslmode="verify-full",
        sslrootcert="/opt/cloudops-desk/certs/us-east-1-bundle.pem",
        connect_timeout=5,
        options="-c statement_timeout=5000",
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

            cursor.execute(
                "SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
            )
            assert cursor.fetchone()[0] is True

    print("PASS: RDS connection, SELECT 1, and verified TLS")


if __name__ == "__main__":
    main()
