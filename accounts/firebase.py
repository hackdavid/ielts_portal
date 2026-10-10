"""Verify Firebase ID tokens (Google sign-in) on the server."""

import json
import time

import firebase_admin
import google.auth.credentials
from django.conf import settings
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError


class FirebaseAuthError(Exception):
    """Token rejected; the message is safe to show to the user."""


class _AnonymousCredential(credentials.Base):
    """Token verification only needs Google's public certs, not a service account."""

    def get_credential(self):
        return google.auth.credentials.AnonymousCredentials()


def _app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        cred = _AnonymousCredential()
        if settings.FIREBASE_SERVICE_ACCOUNT_JSON:
            cred = credentials.Certificate(
                json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            )
        return firebase_admin.initialize_app(
            cred, {"projectId": settings.FIREBASE_PROJECT_ID}
        )


def verify_id_token(id_token):
    """Return decoded claims; signature, audience, issuer and expiry are checked."""
    if not settings.FIREBASE_PROJECT_ID:
        raise FirebaseAuthError("Sign-in is not configured.")
    try:
        return auth.verify_id_token(id_token, app=_app(), clock_skew_seconds=10)
    except (ValueError, FirebaseError) as exc:
        raise FirebaseAuthError("Invalid or expired sign-in token.") from exc


def validate_claims(claims, now=None):
    """Extra policy on top of signature checks: Google only, verified, fresh."""
    now = now if now is not None else time.time()
    if claims.get("firebase", {}).get("sign_in_provider") != "google.com":
        raise FirebaseAuthError("Please sign in with Google.")
    email = (claims.get("email") or "").strip().lower()
    if not email or claims.get("email_verified") is not True:
        raise FirebaseAuthError("Your Google email address is not verified.")
    if now - float(claims.get("auth_time", 0)) > settings.FIREBASE_MAX_AUTH_AGE_SECONDS:
        raise FirebaseAuthError("Sign-in expired, please try again.")
    allowed = settings.FIREBASE_ALLOWED_EMAIL_DOMAINS
    if allowed and email.rsplit("@", 1)[-1] not in allowed:
        raise FirebaseAuthError("This Google account is not allowed.")
    return email
