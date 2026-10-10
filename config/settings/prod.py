"""Production settings stub. Requires DJANGO_SECRET_KEY and DJANGO_ALLOWED_HOSTS."""

from .base import *  # noqa: F403
from .base import os

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
