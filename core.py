import os, re, secrets
from functools import wraps
from datetime import datetime, timezone
from flask import Flask, request, session, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()
db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)

    def public(self):
        return dict(id=self.id, name=self.name, email=self.email, admin=self.admin)


class Invalid(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def text(data, key, maximum=200, required=True):
    value = data.get(key, "")
    if not isinstance(value, str):
        raise Invalid(f"{key.capitalize()} must be text.")
    value = value.strip()
    if required and not value:
        raise Invalid(f"{key.capitalize()} is required.")
    if len(value) > maximum:
        raise Invalid(f"{key.capitalize()} is too long.")
    return value


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise Invalid("Send a JSON object.")
    return data


def login_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not g.user:
            raise Invalid("Please sign in to continue.", 401)
        return fn(*args, **kwargs)

    return inner


def admin_required(fn):
    @wraps(fn)
    @login_required
    def inner(*args, **kwargs):
        if not g.user.admin:
            raise Invalid("Administrator access required.", 403)
        return fn(*args, **kwargs)

    return inner


def owned(model, item_id):
    item = db.session.get(model, item_id)
    if not item:
        raise Invalid("Not found.", 404)
    if item.user_id != g.user.id:
        raise Invalid("You can only change your own content.", 403)
    return item


def make_app(name, config=None, auth=True):
    app = Flask(name)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///app.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("APP_ENV") == "production",
        MAX_CONTENT_LENGTH=100_000,
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
        raise RuntimeError(
            "Set SECRET_KEY to a random value of at least 32 characters."
        )
    db.init_app(app)

    @app.before_request
    def session_setup():
        session.setdefault("csrf", secrets.token_urlsafe(32))
        g.user = (
            db.session.get(User, session["user_id"]) if session.get("user_id") else None
        )
        if request.path.startswith("/api/") and request.method in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            if not secrets.compare_digest(
                request.headers.get("X-CSRF-Token", ""), session["csrf"]
            ):
                raise Invalid("Session expired. Reload the page and try again.", 403)

    @app.get("/api/session")
    def session_info():
        return jsonify(user=g.user.public() if g.user else None, csrf=session["csrf"])

    @app.get("/api/health")
    def health():
        db.session.execute(db.text("SELECT 1"))
        return {"status": "ok"}

    @app.errorhandler(Invalid)
    def invalid(e):
        db.session.rollback()
        return jsonify(error=e.message), e.status

    @app.errorhandler(IntegrityError)
    def duplicate(e):
        db.session.rollback()
        return jsonify(error="This record already exists or is still in use."), 409

    if auth:

        @app.post("/api/register")
        def register():
            data = payload()
            name = text(data, "name", 80)
            email = text(data, "email", 180).lower()
            password = text(data, "password", 128)
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                raise Invalid("Enter a valid email address.")
            if len(password) < 8:
                raise Invalid("Use at least 8 characters for your password.")
            user = User(
                name=name, email=email, password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            session["csrf"] = secrets.token_urlsafe(32)
            return jsonify(user=user.public(), csrf=session["csrf"]), 201

        @app.post("/api/login")
        def login():
            data = payload()
            email = text(data, "email", 180).lower()
            password = text(data, "password", 128)
            user = db.session.scalar(db.select(User).where(User.email == email))
            if not user or not check_password_hash(user.password_hash, password):
                raise Invalid("Email or password is incorrect.", 401)
            session.clear()
            session["user_id"] = user.id
            session["csrf"] = secrets.token_urlsafe(32)
            return jsonify(user=user.public(), csrf=session["csrf"])

        @app.post("/api/logout")
        def logout():
            session.clear()
            session["csrf"] = secrets.token_urlsafe(32)
            return jsonify(user=None, csrf=session["csrf"])

    return app
