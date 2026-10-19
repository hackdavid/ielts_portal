# QA demo data

`qa_demo.sqlite3` is the local SQLite database used to QA the exam-player UX (PR #9):
seeded catalogue (IELTS Academic/General, PTE Academic/Core — 84 question types,
186 questions, 6 mock packs, 4 scoring configs), generated listening audio and a few
student attempts. `media/` holds the 18 audio/image files its `Asset` rows point to.

Dev-only logins (never use these anywhere real):

| user      | password       | role               |
|-----------|----------------|--------------------|
| `admin`   | `admin12345`   | superuser (/admin) |
| `student` | `student12345` | student            |

## Use it

```bash
uv run python scripts/setup_demo_data.py   # copies db + media if missing, then migrates
uv run python manage.py runserver
```

The script skips anything already in place, so it is safe to re-run. `--force`
replaces an existing `db.sqlite3` (the old one is kept as `db.sqlite3.bak`). It honours
`DJANGO_SQLITE_PATH`. If `R2_BUCKET_NAME` is set in your shell, start the server with
`MEDIA_STORAGE=local` so the local media files are used.

Firebase isn't needed: sign in at `/admin/login/` (admin) or use a Django session.
