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
cp data/qa_demo.sqlite3 db.sqlite3      # work on a copy; db.sqlite3 is gitignored
mkdir -p media && cp -r data/media/. media/
uv run python manage.py migrate          # applies any newer migrations
MEDIA_STORAGE=local uv run python manage.py runserver
```

Firebase isn't needed: sign in at `/admin/login/` (admin) or use a Django session.
