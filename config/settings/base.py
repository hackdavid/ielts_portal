"""Base settings shared by every environment (see dev.py / prod.py)."""

import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Project apps
    "core",
    "accounts",
    "tenancy",
    "catalog",
    "attempts",
    "scoring",
    "analytics",
    "plans",
    "institute",
    "pages",
    "content",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.AuthContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site",
                "core.context_processors.app_nav",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database: SQLite for local development; PostgreSQL planned for prod.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_SQLITE_PATH", BASE_DIR / "db.sqlite3"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-gb"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Cloudflare R2 (S3 API) for media when R2_BUCKET_NAME is set; local disk otherwise.
# Objects stay private and are served with short-lived presigned URLs.
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"
if R2_BUCKET_NAME and not TESTING and os.environ.get("MEDIA_STORAGE", "r2") == "r2":
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": R2_BUCKET_NAME,
            "endpoint_url": os.environ.get("R2_ENDPOINT_URL", ""),
            "access_key": os.environ.get("R2_ACCESS_KEY_ID", ""),
            "secret_key": os.environ.get("R2_SECRET_ACCESS_KEY", ""),
            "region_name": "auto",
            "signature_version": "s3v4",
            "location": os.environ.get("R2_ROOT_PREFIX", "").strip("/"),
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": int(os.environ.get("R2_URL_EXPIRE_SEC", "1800")),
            "file_overwrite": False,
        },
    }

# Content pipeline (content app). Every provider falls back to a labelled mock
# when its key/model is missing, so the pipeline runs end to end offline.
CONTENT_LLM_API_KEY = os.environ.get(
    "CONTENT_LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "")
)
CONTENT_LLM_BASE_URL = os.environ.get("CONTENT_LLM_BASE_URL", "")
CONTENT_LLM_MODEL = os.environ.get("CONTENT_LLM_MODEL", "gpt-4o-mini")
CONTENT_LLM_WRITER_MODEL = os.environ.get("CONTENT_LLM_WRITER_MODEL", "")
CONTENT_EMBEDDING_MODEL = os.environ.get(
    "CONTENT_EMBEDDING_MODEL", "text-embedding-3-small"
)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
# Piper TTS: one small multi-speaker voice (en_GB-vctk-medium, ~77 MB, CPU only).
CONTENT_TTS_DIR = os.environ.get(
    "CONTENT_TTS_DIR", str(Path.home() / ".cache" / "ielts_portal" / "piper")
)
CONTENT_TTS_VOICE = os.environ.get("CONTENT_TTS_VOICE", "en_GB-vctk-medium")
CONTENT_TTS_ENABLED = os.environ.get("CONTENT_TTS_ENABLED", "1") == "1"
# Run jobs in a background thread when queued from admin (dev); else use the
# `manage.py run_content_jobs` worker.
CONTENT_JOBS_INLINE = os.environ.get("CONTENT_JOBS_INLINE", "1") == "1"
# Publishing drafts made by mock providers is allowed only when DEBUG is on.
CONTENT_ALLOW_MOCK_PUBLISH = os.environ.get("CONTENT_ALLOW_MOCK_PUBLISH", "")
CONTENT_DEDUP = {
    "minhash_duplicate": 0.6,
    "minhash_similar": 0.4,
    "embedding_duplicate": 0.92,
    "embedding_similar": 0.85,
    "copy_minhash": 0.3,
    "copy_run_words": 12,
}

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:home"

# Google sign-in popups need to talk back to the opener window.
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

# Firebase Authentication (Google sign-in). Web config values are public, not secrets.
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")
FIREBASE_WEB_CONFIG = {
    "apiKey": os.environ.get("FIREBASE_WEB_API_KEY", ""),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
    "projectId": FIREBASE_PROJECT_ID,
    "appId": os.environ.get("FIREBASE_APP_ID", ""),
}
FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
FIREBASE_AUTH_EMULATOR_HOST = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST", "")
FIREBASE_ALLOWED_EMAIL_DOMAINS = [
    d.strip().lower()
    for d in os.environ.get("FIREBASE_ALLOWED_EMAIL_DOMAINS", "").split(",")
    if d.strip()
]
FIREBASE_MAX_AUTH_AGE_SECONDS = 300
FIREBASE_LOGIN_RATE_LIMIT_PER_MINUTE = 10

# Score attempts right after submission. Set False when a worker runs
# `manage.py score_attempts` instead.
SCORING_INLINE = os.environ.get("SCORING_INLINE", "1") == "1"

CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "hello@ieltsportal.app")

PRACTICE_SCORE_DISCLAIMER = (
    "Practice scores are approximations — not official Pearson/IELTS results."
)

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
