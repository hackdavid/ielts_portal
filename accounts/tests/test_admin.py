from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role


class UserAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            "admin", "admin@example.com", "pass"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_add_user_creates_single_profile(self):
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "username": "newstudent",
                "usable_password": "true",
                "password1": "S3cure-pass-123",
                "password2": "S3cure-pass-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="newstudent")
        self.assertEqual(user.profile.role_primary, Role.STUDENT)

    def test_profile_inline_only_on_change_form(self):
        add = self.client.get(reverse("admin:accounts_user_add"))
        self.assertNotContains(add, "profile-0-display_name")
        change = self.client.get(
            reverse("admin:accounts_user_change", args=[self.superuser.pk])
        )
        self.assertContains(change, "profile-0-display_name")
