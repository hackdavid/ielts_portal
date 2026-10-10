"""Local development settings (SQLite, DEBUG on)."""

from .base import *  # noqa: F403
from .base import FIREBASE_WEB_CONFIG, os

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Public web config of the shared dev Firebase project; env vars override it.
_DEV_FIREBASE_WEB_CONFIG = {
    "apiKey": "AIzaSyBJYZJitzKSf-BcSfEhsn-uqm6wMHCa49g",
    "authDomain": "testing-32018.firebaseapp.com",
    "projectId": "testing-32018",
    "appId": "1:863405975742:web:babbf63be00659442c16ef",
}
FIREBASE_WEB_CONFIG = {
    key: value or _DEV_FIREBASE_WEB_CONFIG[key]
    for key, value in FIREBASE_WEB_CONFIG.items()
}
FIREBASE_PROJECT_ID = FIREBASE_WEB_CONFIG["projectId"]
