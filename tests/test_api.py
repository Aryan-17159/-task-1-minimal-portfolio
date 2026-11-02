import pytest
from app import create_app
from core import db, User


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret-at-least-thirty-two-characters",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.db"),
        }
    )


def client(app):
    c = app.test_client()
    c.csrf = c.get("/api/session").json["csrf"]
    return c


def call(c, path, method="GET", body=None):
    r = c.open(
        "/api" + path, method=method, json=body, headers={"X-CSRF-Token": c.csrf}
    )
    if r.is_json and isinstance(r.json, dict) and r.json.get("csrf"):
        c.csrf = r.json["csrf"]
    return r


def register(c, email="person@example.com"):
    r = call(
        c,
        "/register",
        "POST",
        {
            "name": "Test person",
            "email": email,
            "password": "test-password-123",
            "admin": True,
        },
    )
    assert r.status_code == 201
    assert r.json["user"]["admin"] is False
    return r.json["user"]


def test_portfolio_content_contact_and_csrf(app, monkeypatch):
    c = client(app)
    assert app.test_cli_runner().invoke(args=["seed"]).exit_code == 0
    assert len(call(c, "/projects").json) == 3
    assert c.post("/api/contact", json={"name": "A"}).status_code == 403
    assert (
        call(
            c, "/contact", "POST", {"name": "A", "email": "bad", "message": "Hello"}
        ).status_code
        == 400
    )
    valid = {
        "name": "Visitor",
        "email": "visitor@example.com",
        "message": "A real contact message",
    }
    for _ in range(5):
        assert call(c, "/contact", "POST", valid).status_code == 201
    assert call(c, "/contact", "POST", valid).status_code == 429
    assert (
        call(c, "/projects", "POST", {"title": "x", "summary": "y"}).status_code == 403
    )
    from app import Message

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Message)) == 5
    assert call(c, "/messages").status_code == 403
    monkeypatch.setenv("ADMIN_KEY", "test-administrator-key")
    inbox = c.get("/api/messages", headers={"X-Admin-Key": "test-administrator-key"})
    assert inbox.status_code == 200
    assert len(inbox.json) == 5
    assert inbox.json[0]["email"] == "visitor@example.com"
