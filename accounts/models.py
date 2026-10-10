from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel


class User(AbstractUser):
    """Custom user so auth fields can evolve without a painful swap later."""


class Role(models.TextChoices):
    STUDENT = "student", "Student"
    TUTOR = "tutor", "Tutor"
    INSTITUTE_ADMIN = "institute_admin", "Institute admin"
    SUPER_ADMIN = "super_admin", "Super admin"


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    display_name = models.CharField(max_length=150, blank=True)
    role_primary = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT
    )
    primary_exam = models.ForeignKey(
        "catalog.Exam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    target_score = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="PTE 10-90 or IELTS band 0-9.",
    )
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    free_mocks_remaining = models.PositiveIntegerField(default=1)
    onboarded_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.display_name or self.user.get_username()
