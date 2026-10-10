import json
import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from tenancy.models import AccessInvite, Membership, Tenant

User = get_user_model()


def google_login(client, email, uid=None):
    claims = {
        "uid": uid or f"uid-{email}",
        "email": email,
        "email_verified": True,
        "name": email.split("@")[0],
        "auth_time": time.time(),
        "firebase": {"sign_in_provider": "google.com"},
    }
    with mock.patch("accounts.views.verify_id_token", return_value=claims):
        return client.post(
            reverse("accounts:firebase_login"),
            json.dumps({"id_token": "t"}),
            content_type="application/json",
        )


class RoleAndInviteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Tenant.objects.create(slug="acme", name="Acme Institute")

    def setUp(self):
        cache.clear()

    def test_org_invites_route_to_org_dashboard_for_each_email(self):
        for email in ("Owner@Acme.com", "manager@acme.com"):
            AccessInvite.objects.create(tenant=self.org, email=email, role="org")
        for email in ("owner@acme.com", "MANAGER@acme.com"):
            with self.subTest(email):
                self.client.logout()
                response = google_login(self.client, email)
                self.assertEqual(
                    response.json()["redirect"], reverse("institute:console")
                )
                self.assertEqual(self.client.session["auth_context"]["role"], Role.ORG)
                self.assertEqual(
                    self.client.session["auth_context"]["tenant_name"], "Acme Institute"
                )
                page = self.client.get(reverse("institute:console"))
                self.assertContains(page, "Acme Institute")
                self.assertContains(page, "Org · Acme Institute")
        invite = AccessInvite.objects.get(email="owner@acme.com")
        self.assertIsNotNone(invite.accepted_at)
        self.assertEqual(
            Membership.objects.filter(tenant=self.org, role="org").count(), 2
        )

    def test_student_invite_joins_org_and_uses_student_dashboard(self):
        AccessInvite.objects.create(
            tenant=self.org, email="kid@school.com", role="student"
        )
        self.assertEqual(
            google_login(self.client, "kid@school.com").json()["redirect"],
            reverse("accounts:onboarding"),
        )
        user = User.objects.get(email="kid@school.com")
        user.profile.onboarded_at = timezone.now()
        user.profile.save()
        page = self.client.get(reverse("analytics:dashboard"))
        self.assertContains(page, "Student · Acme Institute")
        self.assertEqual(self.client.get(reverse("institute:console")).status_code, 403)

    def test_uninvited_user_is_default_independent_student(self):
        google_login(self.client, "solo@gmail.com")
        context = self.client.session["auth_context"]
        self.assertEqual(
            context, {"role": "student", "tenant_id": None, "tenant_name": ""}
        )
        self.assertFalse(Membership.objects.exists())
        self.assertEqual(self.client.get(reverse("institute:console")).status_code, 403)

    def test_invite_added_after_signup_applies_without_relogin(self):
        google_login(self.client, "late@acme.com")
        AccessInvite.objects.create(tenant=self.org, email="late@acme.com", role="org")
        self.assertEqual(
            self.client.get(reverse("accounts:me")).json()["role"], Role.ORG
        )
        self.assertEqual(self.client.get(reverse("institute:console")).status_code, 200)

    def test_backend_revocation_is_enforced_on_next_request(self):
        AccessInvite.objects.create(tenant=self.org, email="boss@acme.com", role="org")
        google_login(self.client, "boss@acme.com")
        Membership.objects.filter(user__email="boss@acme.com").update(is_active=False)
        self.assertEqual(self.client.get(reverse("institute:console")).status_code, 403)
        self.assertEqual(self.client.session["auth_context"]["role"], Role.STUDENT)
        User.objects.filter(email="boss@acme.com").update(is_active=False)
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("accounts:login")))
        self.assertEqual(
            self.client.get(reverse("accounts:me")).json(), {"authenticated": False}
        )

    def test_inactive_org_drops_access(self):
        AccessInvite.objects.create(tenant=self.org, email="o@acme.com", role="org")
        google_login(self.client, "o@acme.com")
        Tenant.objects.filter(pk=self.org.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse("institute:console")).status_code, 403)

    def test_superuser_goes_to_django_admin(self):
        User.objects.create_superuser("root", "root@example.com", "pw")
        response = google_login(self.client, "root@example.com")
        self.assertEqual(response.json()["redirect"], reverse("admin:index"))
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse("analytics:dashboard")),
            reverse("admin:index"),
            fetch_redirect_response=False,
        )

    def test_anonymous_redirected_and_authenticated_pages_not_cached(self):
        for name in ("analytics:dashboard", "accounts:onboarding", "institute:console"):
            with self.subTest(name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    response["Location"].startswith(reverse("accounts:login"))
                )
        google_login(self.client, "c@x.com")
        response = self.client.get(reverse("accounts:onboarding"))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn('data-authenticated="true"', response.content.decode())

    def test_navbar_reflects_backend_session(self):
        self.assertContains(self.client.get("/"), "Login / Register")
        google_login(self.client, "nav@x.com")
        page = self.client.get("/")
        self.assertContains(page, 'data-testid="logout"')
        self.assertContains(page, "Dashboard")
        self.assertNotContains(page, "Login / Register")
        self.client.post(reverse("accounts:logout"))
        self.assertContains(self.client.get("/"), "Login / Register")

    def test_admin_tenant_page_has_access_email_inline(self):
        admin = User.objects.create_superuser("adm", "adm@example.com", "pw")
        self.client.force_login(admin)
        page = self.client.get(
            reverse("admin:tenancy_tenant_change", args=[self.org.pk])
        )
        self.assertContains(page, "Access emails")
