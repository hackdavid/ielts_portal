# ielts_portal

PTE + IELTS practice portal — Django 5.2, Django Templates, Tailwind CSS, Alpine.js, Motion One.

- Product & engineering playbook: [`docs/playbook/`](docs/playbook/00-README.md)
- Phase-wise progress: [`docs/TRACKER.md`](docs/TRACKER.md)
- Auth design (Google via Firebase): [`docs/playbook/07-authentication-firebase.md`](docs/playbook/07-authentication-firebase.md)

## Layout

| Path | Purpose |
|------|---------|
| `config/` | Project package; settings split into `settings/base.py`, `dev.py` (default for `manage.py`), `prod.py` (default for WSGI/ASGI) |
| `pages/` | Public pages (landing, about, contact) |
| `core/` | Shared base models (`TimeStampedModel`), context processors, `/api/health/`, `manage.py tailwind` |
| `accounts/` | Custom `User` + `UserProfile` |
| `tenancy/` | `Tenant`, `Membership` |
| `catalog/` | `Exam`, `QuestionType`, `Question`, `Asset`, `Tag`, `MockPack`, `MockPackItem`, `StudyAid` |
| `attempts/` | `Attempt`, `AttemptItem`, `FeedbackNote` |
| `scoring/` | `ScoreBreakdown`, `ScoringConfig` |
| `plans/` | `Plan`, `PlanDay`, `PlanEnrolment`, `PlanDayProgress`, `Entitlement` |
| `analytics/`, `institute/` | Placeholders for Phase 5 / 6 views |
| `templates/` | All templates (`base.html`, `components/`, `<app>/…`) |
| `static/src/tailwind.css` | Tailwind source → built to `static/css/app.css` |
| `static/js/api.js` | Central browser API client (`window.api`) — use it for every JSON call |
| `static/vendor/` | Vendored Alpine.js and Motion One |

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). Uses SQLite (`db.sqlite3`) locally.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/ (admin at `/admin/`). Settings read `DJANGO_*` env vars (see `.env.example`).

## Tailwind

`static/css/app.css` is committed, so `runserver` works without a build. After changing templates/classes:

```bash
uv run python manage.py tailwind          # one-off minified build
uv run python manage.py tailwind --watch  # rebuild on change while developing
```

The first run downloads the pinned standalone Tailwind CLI (no Node needed).

## Demo catalogue

`uv run python manage.py seed_demo` creates placeholder question types, 3 questions per type and a free + a locked mock for each exam (safe to re-run). Browse at `/exams/` after signing in.

## Sign-in (Google via Firebase)

`/accounts/login/` → **Continue with Google** (Firebase popup) → the ID token is POSTed once to `/api/auth/firebase/`, verified server-side, and swapped for a normal Django session. No passwords; `/admin/` keeps Django password login for superusers. Dev uses the public web config in `config/settings/dev.py`; set `FIREBASE_*` env vars (see `.env.example`) for other projects. Add every host you serve from to Firebase → Authentication → Settings → Authorized domains. Details: [`docs/playbook/07-authentication-firebase.md`](docs/playbook/07-authentication-firebase.md).

## Frontend API client

```js
const health = await api.get("/health/");             // -> /api/health/
await api.post("/attempts/<id>/items/1/save/", { response: {} });
api.setHeader("Authorization", "Bearer <token>");     // future auth
api.onUnauthorized(() => (location.href = "/accounts/login/"));
```

CSRF is attached automatically on unsafe methods; non-2xx responses throw `api.ApiError`.

## Checks

```bash
uv run python manage.py test
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check .
```
