import pytest

from app import create_app
from app.models import db


@pytest.fixture
def client():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    with app.app_context():
        db.create_all()

    yield app.test_client()

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_create_and_retrieve_ticket(client):
    response = client.post(
        "/tickets",
        json={"title": "Cannot access account", "description": "Login fails"},
    )
    assert response.status_code == 201
    ticket_id = response.json["id"]

    saved = client.get(f"/tickets/{ticket_id}")
    assert saved.status_code == 200
    assert saved.json["title"] == "Cannot access account"
    assert saved.json["description"] == "Login fails"
    assert saved.json["status"] == "open"

    listing = client.get("/tickets")
    assert listing.status_code == 200
    assert listing.json == [saved.json]


def test_reject_empty_title(client):
    response = client.post("/tickets", json={"title": "   "})
    assert response.status_code == 400
    assert client.get("/tickets").json == []


def test_unknown_ticket(client):
    response = client.get("/tickets/999")
    assert response.status_code == 404


def test_reject_invalid_json_body(client):
    response = client.post("/tickets", json=["invalid"])
    assert response.status_code == 400


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"CloudOps Desk" in response.data
    assert b'id="ticket-form"' in response.data
