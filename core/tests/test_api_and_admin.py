from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

PROJECT_APPS = {"accounts", "tenancy", "catalog", "attempts", "scoring", "plans"}


class HealthApiTests(TestCase):
    def test_health_returns_json(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_health_rejects_post(self):
        self.assertEqual(self.client.post(reverse("core:health")).status_code, 405)


class AdminRegistrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            "admin", "admin@example.com", "pass"
        )

    def project_models(self):
        return [m for m in apps.get_models() if m._meta.app_label in PROJECT_APPS]

    def test_every_project_model_is_registered(self):
        missing = [
            m.__name__ for m in self.project_models() if not admin.site.is_registered(m)
        ]
        self.assertEqual(missing, [])

    def test_admin_changelist_and_add_pages_load(self):
        self.client.force_login(self.superuser)
        for model in self.project_models():
            opts = model._meta
            for view in ("changelist", "add"):
                url = reverse(f"admin:{opts.app_label}_{opts.model_name}_{view}")
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)
