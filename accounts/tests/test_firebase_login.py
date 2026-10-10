import json
import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.firebase import FirebaseAuthError, verify_id_token
from accounts.models import Role
from catalog.models import Exam

User = get_user_model()


def make_claims(**overrides):
    claims = {
        "uid": "google-uid-1",
        "email": "Student@Example.com",
        "email_verified": True,
        "name": "Asha Student",
        "picture": "https://lh3.googleusercontent.com/a/photo",
        "auth_time": time.time(),
        "firebase": {"sign_in_provider": "google.com"},
    }
    claims.update(overrides)
    return claims


class FirebaseLoginTests(TestCase):
    url = reverse("accounts:firebase_login")

    def setUp(self):
        cache.clear()

    def post(self, claims=None, side_effect=None, **body):
        body.setdefault("id_token", "token")
        with mock.patch(
            "accounts.views.verify_id_token",
            return_value=claims if claims is not None else make_claims(),
            side_effect=side_effect,
        ):
            return self.client.post(
                self.url, json.dumps(body), content_type="application/json"
            )

    def test_first_sign_in_creates_user_and_session(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redirect"], reverse("accounts:onboarding"))
        user = User.objects.get(firebase_uid="google-uid-1")
        self.assertEqual(user.email, "student@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.display_name, "Asha Student")
        self.assertEqual(user.profile.role_primary, Role.STUDENT)
        self.assertTrue(user.profile.avatar_url)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_returning_onboarded_user_goes_to_dashboard_or_safe_next(self):
        self.post()
        user = User.objects.get(firebase_uid="google-uid-1")
        user.profile.onboarded_at = timezone.now()
        user.profile.save()
        self.client.logout()
        self.assertEqual(self.post().json()["redirect"], reverse("analytics:dashboard"))
        self.client.logout()
        self.assertEqual(self.post(next="/about/").json()["redirect"], "/about/")
        self.client.logout()
        evil = self.post(next="https://evil.example/").json()["redirect"]
        self.assertEqual(evil, reverse("analytics:dashboard"))
        self.assertEqual(User.objects.count(), 1)

    def test_existing_email_is_linked_not_duplicated(self):
        invited = User.objects.create(username="invited", email="student@example.com")
        self.assertEqual(self.post().status_code, 200)
        invited.refresh_from_db()
        self.assertEqual(invited.firebase_uid, "google-uid-1")
        self.assertEqual(User.objects.count(), 1)

    def test_email_owned_by_other_firebase_uid_is_rejected(self):
        User.objects.create(
            username="other", email="student@example.com", firebase_uid="x"
        )
        self.assertEqual(self.post().status_code, 401)

    def test_policy_rejections(self):
        cases = {
            "password provider": make_claims(firebase={"sign_in_provider": "password"}),
            "unverified": make_claims(email_verified=False),
            "stale": make_claims(auth_time=time.time() - 3600),
            "no email": make_claims(email=""),
        }
        for label, claims in cases.items():
            with self.subTest(label):
                response = self.post(claims)
                self.assertEqual(response.status_code, 401)
                self.assertIn("error", response.json())
                self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(User.objects.exists())

    @override_settings(FIREBASE_ALLOWED_EMAIL_DOMAINS=["school.edu"])
    def test_domain_allow_list(self):
        self.assertEqual(self.post().status_code, 401)
        self.assertEqual(self.post(make_claims(email="a@school.edu")).status_code, 200)

    def test_inactive_user_rejected(self):
        User.objects.create(
            username="u", email="x@y.com", firebase_uid="google-uid-1", is_active=False
        )
        self.assertEqual(self.post().status_code, 401)

    def test_invalid_token_and_bad_body(self):
        self.assertEqual(
            self.post(side_effect=FirebaseAuthError("bad")).status_code, 401
        )
        bad = self.client.post(self.url, "not json", content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(
            self.client.post(
                self.url, "{}", content_type="application/json"
            ).status_code,
            400,
        )
        self.assertEqual(self.client.get(self.url).status_code, 405)

    @override_settings(FIREBASE_LOGIN_RATE_LIMIT_PER_MINUTE=2)
    def test_rate_limit(self):
        codes = [
            self.post(side_effect=FirebaseAuthError("bad")).status_code
            for _ in range(3)
        ]
        self.assertEqual(codes, [401, 401, 429])

    def test_logout_and_me(self):
        self.assertEqual(
            self.client.get(reverse("accounts:me")).json(), {"authenticated": False}
        )
        self.post()
        me = self.client.get(reverse("accounts:me")).json()
        self.assertTrue(me["authenticated"])
        self.assertFalse(me["onboarded"])
        self.assertEqual(self.client.post(reverse("accounts:logout")).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_real_verifier_rejects_garbage_without_credentials(self):
        with self.assertRaises(FirebaseAuthError):
            verify_id_token("not-a-jwt")


class PagesAndPermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create(username="s", email="s@example.com")
        cls.superuser = User.objects.create_superuser("root", "r@example.com", "pw")

    def test_login_page_renders_google_button_and_config(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, "Continue with Google")
        self.assertContains(response, 'id="firebase-config"')
        self.assertContains(response, "firebase-login.js")
        self.assertEqual(
            response["Cross-Origin-Opener-Policy"], "same-origin-allow-popups"
        )
        self.assertNotContains(response, 'type="password"')

    def test_register_redirects_to_login(self):
        response = self.client.get(reverse("accounts:register") + "?next=/dashboard/")
        self.assertRedirects(
            response,
            reverse("accounts:login") + "?next=/dashboard/",
            fetch_redirect_response=False,
        )

    def test_onboarding_validates_and_completes(self):
        self.client.force_login(self.student)
        pte = Exam.objects.get(code="PTE_ACADEMIC")
        ielts = Exam.objects.get(code="IELTS_ACADEMIC")
        url = reverse("accounts:onboarding")
        self.assertContains(self.client.get(url), "IELTS General")
        bad = self.client.post(
            url, {"display_name": "S", "primary_exam": ielts.pk, "target_score": "7.3"}
        )
        self.assertEqual(bad.status_code, 200)
        self.assertContains(bad, "steps of 0.5")
        bad = self.client.post(
            url, {"display_name": "S", "primary_exam": pte.pk, "target_score": "95"}
        )
        self.assertContains(bad, "10 to 90")
        ok = self.client.post(
            url,
            {"display_name": "S", "primary_exam": pte.pk, "target_score": "65"},
            follow=True,
        )
        self.assertRedirects(ok, reverse("analytics:dashboard"))
        self.assertContains(ok, "PTE Academic")
        self.student.profile.refresh_from_db()
        self.assertIsNotNone(self.student.profile.onboarded_at)

    def test_nav_shows_sign_in_or_logout(self):
        self.assertContains(self.client.get("/"), "Sign in with Google")
        self.client.force_login(self.student)
        self.assertContains(self.client.get("/"), 'data-testid="logout"')
