from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from app import create_app
from app.models import db


def make_test_app():
    return create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })


def test_ready_when_database_responds():
    app = make_test_app()

    with app.test_client() as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}


def test_database_failure_affects_readiness_not_health():
    app = make_test_app()

    with patch.object(
        db.session,
        "execute",
        side_effect=OperationalError(
            "SELECT 1", {}, Exception("Database unavailable")
        ),
    ):
        with app.test_client() as client:
            ready = client.get("/ready")
            health = client.get("/health")

    assert ready.status_code == 503
    assert ready.get_json() == {"status": "not_ready"}
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok"}
