from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


def default_disclaimer():
    return settings.PRACTICE_SCORE_DISCLAIMER


class ScoreBreakdown(TimeStampedModel):
    class Scale(models.TextChoices):
        PTE_10_90 = "pte_10_90", "PTE 10–90"
        IELTS_BAND = "ielts_band", "IELTS band"

    attempt = models.OneToOneField(
        "attempts.Attempt", on_delete=models.CASCADE, related_name="score_breakdown"
    )
    overall = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    scale = models.CharField(max_length=20, choices=Scale.choices)
    sections = models.JSONField(default=dict, blank=True)
    enabling = models.JSONField(null=True, blank=True, help_text="PTE approximation.")
    traits = models.JSONField(
        null=True, blank=True, help_text="IELTS W/S traits aggregate."
    )
    items_summary = models.JSONField(default=list, blank=True)
    config_version = models.CharField(max_length=50, blank=True)
    scorer_versions = models.JSONField(default=dict, blank=True)
    disclaimer = models.TextField(default=default_disclaimer)
    raw_worker_log = models.JSONField(
        null=True, blank=True, help_text="Super Admin only."
    )

    def __str__(self):
        return f"Score for {self.attempt_id}: {self.overall}"


class ScoringConfig(TimeStampedModel):
    """Practice-approximation weights; one active per (exam, tenant) via services."""

    exam = models.ForeignKey(
        "catalog.Exam", on_delete=models.CASCADE, related_name="scoring_configs"
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scoring_configs",
        help_text="Empty = platform default.",
    )
    version = models.CharField(max_length=50, help_text='e.g. "2026.09.1"')
    is_active = models.BooleanField(default=False)
    weights = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default="Practice approximation")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "tenant", "version"], name="uniq_scoringconfig_version"
            )
        ]

    def __str__(self):
        return f"{self.exam.code} {self.version}"
