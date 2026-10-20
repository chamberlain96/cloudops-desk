from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import os

import click
from flask import Flask, jsonify, request, render_template

from .models import db, Ticket


def create_app(test_config=None):
    app = Flask(__name__)
    database_url_file = os.environ.get("DATABASE_URL_FILE")

    if database_url_file:
        database_url = Path(database_url_file).read_text().strip()
        if not database_url:
            raise RuntimeError("Database URL file is empty")
    else:
        database_url = os.environ.get(
            "DATABASE_URL", "sqlite:///tickets.db"
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config is not None:
        app.config.update(test_config)

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
    }

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] = {
            "connect_timeout": 5,
        }

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        click.echo("Database initialized.")
    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/ready")
    def ready():
        try:
            db.session.execute(text("SELECT 1")).scalar_one()
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify(status="not_ready"), 503

        return jsonify(status="ready"), 200

    @app.post("/tickets")
    def create_ticket():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Send a JSON object"), 400

        title = data.get("title")
        description = data.get("description", "")

        if not isinstance(title, str) or not title.strip():
            return jsonify(error="Title is required"), 400
        if not isinstance(description, str):
            return jsonify(error="Description must be text"), 400

        ticket = Ticket(title=title.strip(), description=description)
        db.session.add(ticket)
        db.session.commit()

        return jsonify(ticket.to_dict()), 201

    @app.get("/tickets")
    def list_tickets():
        tickets = db.session.execute(
            db.select(Ticket).order_by(Ticket.id)
        ).scalars().all()
        return jsonify([ticket.to_dict() for ticket in tickets]), 200

    @app.get("/tickets/<int:ticket_id>")
    def get_ticket(ticket_id):
        ticket = db.session.get(Ticket, ticket_id)
        if ticket is None:
            return jsonify(error="Ticket not found"), 404
        return jsonify(ticket.to_dict()), 200

    return app
