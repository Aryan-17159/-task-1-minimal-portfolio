# Minimal Portfolio

A personal portfolio with a quiet two-column layout, a database-backed project list, project details, education, and a contact form.

Built from new source for task 1. The interface uses a restrained palette, fine dividers, system fonts, native dialogs, and responsive layouts. Each project is self-contained.

![Desktop screenshot](docs/desktop.png)

[View mobile screenshot](docs/mobile.png)

## Run locally

Requires Python 3.12. Run commands from this project directory:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into `SECRET_KEY` in `.env`. Use a different value for each application. On Windows, activate with `.venv\Scripts\activate`.

```sh
flask --app app:create_app seed
python app.py
```

Open http://localhost:5200. `PORT` can override that port. SQLite creates a persistent local database in `instance/app.db`. Seed commands preserve existing records. No credentials or databases are bundled.

## Using the app

The contact form saves messages to the database; it does not send email. Set a private `ADMIN_KEY` environment variable to read the newest 100 messages through `GET /api/messages` with the `X-Admin-Key` header. That key also allows project creation and deletion through the API. Keep it on the server, never in browser code.

## Backend and database

Flask serves the HTML, static assets, and JSON API from one origin. SQLAlchemy stores the data. Passwords are hashed with Werkzeug; sessions use HTTP-only, SameSite cookies. Each application has a separate session cookie name. All state-changing API requests require the CSRF token returned by `GET /api/session` in an `X-CSRF-Token` header. Authentication responses rotate that token. User-entered content is rendered as text.

For PostgreSQL, set `DATABASE_URL=postgresql://user:password@host/database`. Tables are created at startup for a fresh installation. Existing production schemas require planned migrations when models change.

## Deploy

Use a Python web host with a durable PostgreSQL database. Set `SECRET_KEY`, `DATABASE_URL`, and `APP_ENV=production` in the host's environment. Install dependencies with `pip install -r requirements.txt`, then start with:

```sh
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

Use HTTPS: production mode enables Secure cookies. Run the seed command once if sample content is wanted. A `Procfile` is included. Hosting and database provisioning are separate from the source project; no live deployment is claimed.

## Verify

```sh
pip install -r requirements-dev.txt
python -m pytest -q
```

API coverage: Project seed data, contact validation, rate limits, CSRF protection, and private inbox access.

The browser flows were also exercised at 1440px and 390px, with no JavaScript errors or horizontal overflow. Screenshots are from those local checks. Automated database tests use SQLite; PostgreSQL concurrency has not been load-tested.

## Publish as a separate repository

Suggested repository: `Aryan-17159/task-1-minimal-portfolio`. From this directory, after signing into GitHub CLI with an account allowed to create repositories:

```sh
git init -b main
git add .
git commit -m "Build minimal portfolio application"
gh repo create Aryan-17159/task-1-minimal-portfolio --public --source=. --remote=origin --push
```

If this directory already has a Git history, skip the initialization and commit steps. Never commit `.env`, runtime databases, or credentials.
