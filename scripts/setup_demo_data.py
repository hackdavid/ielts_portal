"""Set up the local QA demo data, then you can run the dev server.

Run from the repo root (uv installs the dependencies on first run):

    uv run python scripts/setup_demo_data.py          # copy what's missing, migrate
    uv run python scripts/setup_demo_data.py --force  # replace db (backup kept)
    uv run python manage.py runserver

Each step is skipped when it is already done, so it is safe to run again.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEMO_DB = DATA / "qa_demo.sqlite3"
DEMO_MEDIA = DATA / "media"
MEDIA = ROOT / "media"


def target_db() -> Path:
    path = Path(os.environ.get("DJANGO_SQLITE_PATH", ROOT / "db.sqlite3"))
    return path if path.is_absolute() else ROOT / path


def setup_db(force: bool) -> None:
    db = target_db()
    if db.exists() and db.stat().st_size > 0 and not force:
        print(f"[skip] database already exists: {db} (use --force to replace)")
        return
    if db.exists() and db.stat().st_size > 0:
        backup = db.with_name(db.name + ".bak")
        shutil.copy2(db, backup)
        print(f"[backup] {db} -> {backup}")
    db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEMO_DB, db)
    print(f"[done] copied demo database -> {db}")


def setup_media() -> None:
    copied = skipped = 0
    for src in DEMO_MEDIA.rglob("*"):
        if not src.is_file():
            continue
        dest = MEDIA / src.relative_to(DEMO_MEDIA)
        if dest.exists():
            skipped += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1
    if copied:
        print(
            f"[done] copied {copied} media file(s) to {MEDIA} ({skipped} already there)"
        )
    else:
        print(f"[skip] all {skipped} demo media files already in {MEDIA}")


def migrate() -> None:
    print("[run] manage.py migrate (applies only new migrations)")
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"], cwd=ROOT, check=True
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--force", action="store_true", help="replace an existing database"
    )
    args = parser.parse_args()

    if not DEMO_DB.exists():
        print(f"[error] {DEMO_DB} not found; pull the latest main first.")
        return 1
    try:
        import django  # noqa: F401
    except ImportError:
        print(
            "[error] Django not found. Run with: "
            "uv run python scripts/setup_demo_data.py"
        )
        return 1

    setup_db(args.force)
    setup_media()
    migrate()

    print("\nReady. Logins: admin / admin12345 (/admin/), student / student12345")
    print("Start the server with: uv run python manage.py runserver")
    if os.environ.get("R2_BUCKET_NAME"):
        print(
            "R2_BUCKET_NAME is set; prefix MEDIA_STORAGE=local "
            "to use the local media files."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
