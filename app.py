import os, re, secrets, hashlib
from datetime import datetime, timedelta, timezone
from flask import render_template, request, jsonify
from core import db, make_app, payload, text, Invalid


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    detail = db.Column(db.Text, default="")
    tags = db.Column(db.JSON, default=list)
    year = db.Column(db.String(4), default="2026")

    def public(self):
        return {
            k: getattr(self, k)
            for k in ["id", "title", "summary", "detail", "tags", "year"]
        }


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    email = db.Column(db.String(180))
    body = db.Column(db.Text)
    source = db.Column(db.String(64))
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


def create_app(config=None):
    app = make_app(__name__, config, auth=False)
    app.config["SESSION_COOKIE_NAME"] = "portfolio_session"

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/projects")
    def projects():
        return jsonify(
            [
                p.public()
                for p in db.session.scalars(db.select(Project).order_by(Project.id))
            ]
        )

    def admin():
        key = os.getenv("ADMIN_KEY", "")
        if not key or not secrets.compare_digest(
            request.headers.get("X-Admin-Key", ""), key
        ):
            raise Invalid("Administrator access required.", 403)

    @app.get("/api/messages")
    def messages():
        admin()
        items = db.session.scalars(
            db.select(Message).order_by(Message.id.desc()).limit(100)
        )
        return jsonify(
            [
                dict(
                    id=m.id,
                    name=m.name,
                    email=m.email,
                    message=m.body,
                    created=m.created.isoformat(),
                )
                for m in items
            ]
        )

    @app.post("/api/projects")
    def add_project():
        admin()
        d = payload()
        p = Project(
            title=text(d, "title", 100),
            summary=text(d, "summary", 500),
            detail=text(d, "detail", 5000, False),
            tags=[],
        )
        db.session.add(p)
        db.session.commit()
        return jsonify(p.public()), 201

    @app.delete("/api/projects/<int:item_id>")
    def remove_project(item_id):
        admin()
        p = db.session.get(Project, item_id)
        if not p:
            raise Invalid("Project not found.", 404)
        db.session.delete(p)
        db.session.commit()
        return {"ok": True}

    @app.post("/api/contact")
    def contact():
        d = payload()
        name = text(d, "name", 80)
        email = text(d, "email", 180)
        body = text(d, "message", 5000)
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise Invalid("Enter a valid email address.")
        source = hashlib.sha256((request.remote_addr or "").encode()).hexdigest()
        recent = db.session.scalar(
            db.select(db.func.count())
            .select_from(Message)
            .where(
                Message.source == source,
                Message.created > datetime.now(timezone.utc) - timedelta(minutes=15),
            )
        )
        if recent >= 5:
            raise Invalid("Please wait a little before sending another message.", 429)
        db.session.add(Message(name=name, email=email, body=body, source=source))
        db.session.commit()
        return {"ok": True}, 201

    @app.cli.command("seed")
    def seed():
        if db.session.scalar(db.select(db.func.count()).select_from(Project)):
            print("Projects already exist; nothing replaced.")
            return
        items = [
            (
                "Task manager",
                "A simple place to plan and keep track of work.",
                "An authenticated application for creating tasks, setting priorities and due dates, and keeping completed work separate. Built with owner-specific data and a responsive list interface.",
                ["Python", "Flask", "PostgreSQL"],
            ),
            (
                "Online store",
                "A small catalog with a complete ordering flow.",
                "A database-backed store with a product catalog, cart, inventory checks, customer accounts, order history and an administrator workspace. Demonstration checkout does not process payments.",
                ["Python", "SQLAlchemy", "JavaScript"],
            ),
            (
                "Publishing platform",
                "Writing, reading, and conversations in one place.",
                "A blog with author-only drafts, post editing, topic filters, and a comment section. The interface uses simple reading and writing layouts that adapt to small screens.",
                ["Flask", "PostgreSQL", "HTML / CSS"],
            ),
        ]
        for title, summary, detail, tags in items:
            db.session.add(
                Project(title=title, summary=summary, detail=detail, tags=tags)
            )
        db.session.commit()
        print("Portfolio projects added.")

    with app.app_context():
        db.create_all()
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", 5200)))
