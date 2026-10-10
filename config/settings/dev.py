"""Local development settings (SQLite, DEBUG on)."""

from .base import *  # noqa: F403
from .base import os

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
