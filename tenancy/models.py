from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from core.models import TimeStampedModel


class Tenant(TimeStampedModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    logo = models.FileField(upload_to="tenants/logos/", null=True, blank=True)
    primary_color = models.CharField(max_length=7, default="#0F766E")
    custom_domain = models.CharField(max_length=255, null=True, blank=True, unique=True)
    feature_flags = models.JSONField(default=dict, blank=True)
    seat_limit = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ORG = "org", "Organisation"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_active = models.BooleanField(default=True)
    invited_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user"], name="uniq_membership_tenant_user"
            )
        ]
        indexes = [models.Index(fields=["tenant", "role"])]

    def __str__(self):
        return f"{self.user} @ {self.tenant} ({self.role})"


class AccessInvite(TimeStampedModel):
    """Email granted access to an org by a super admin; applied on Google sign-in."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="invites")
    email = models.EmailField()
    role = models.CharField(
        max_length=20, choices=Membership.Role.choices, default=Membership.Role.STUDENT
    )
    is_active = models.BooleanField(default=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "tenant", Lower("email"), name="uniq_invite_tenant_email"
            )
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} → {self.tenant} ({self.role})"
