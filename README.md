# ielts_portal

Django project for the IELTS Portal.

## Layout

- `config/` – project settings, URLs, WSGI/ASGI
- `pages/` – public pages app (home, about, contact)
- `templates/base.html` – shared site layout
- `static/` – project-wide static assets

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
# Optional: settings read DJANGO_* env vars (see .env.example)
uv run python manage.py migrate
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/.

## Checks

```bash
uv run python manage.py test
uv run ruff check .
uv run ruff format --check .
```
