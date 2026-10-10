from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Plan(TimeStampedModel):
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="plans",
        help_text="Empty = platform catalogue.",
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    exam = models.ForeignKey(
        "catalog.Exam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans",
    )
    days_count = models.PositiveIntegerField()
    price_stub = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    entitlements = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_plan_tenant_code"
            )
        ]

    def __str__(self):
        return self.name


class PlanDay(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="days")
    day_index = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    tasks = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["plan", "day_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "day_index"], name="uniq_planday_plan_day"
            )
        ]

    def __str__(self):
        return f"{self.plan} · Day {self.day_index}"


class PlanEnrolment(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="plan_enrolments",
    )
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="enrolments")
    started_on = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    def __str__(self):
        return f"{self.user} → {self.plan}"


class PlanDayProgress(TimeStampedModel):
    enrolment = models.ForeignKey(
        PlanEnrolment, on_delete=models.CASCADE, related_name="day_progress"
    )
    day_index = models.PositiveIntegerField()
    completed_tasks = models.JSONField(default=list, blank=True)
    is_done = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "plan day progress"
        constraints = [
            models.UniqueConstraint(
                fields=["enrolment", "day_index"],
                name="uniq_plandayprogress_enrolment_day",
            )
        ]

    def __str__(self):
        return f"{self.enrolment} · Day {self.day_index}"


class Entitlement(TimeStampedModel):
    class Source(models.TextChoices):
        SIGNUP = "signup", "Signup"
        INSTITUTE = "institute", "Institute"
        PURCHASE_STUB = "purchase_stub", "Purchase (stub)"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="entitlements",
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="entitlements",
    )
    key = models.CharField(
        max_length=100, help_text="e.g. free_mock_pte, pack:123, unlimited"
    )
    value = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.SIGNUP
    )

    class Meta:
        indexes = [models.Index(fields=["user", "key"])]

    def __str__(self):
        return f"{self.key} ({self.user or self.tenant})"
