import uuid

from django.conf import settings
from django.db import models

from catalog.models import PracticeMode, Section
from core.models import TimeStampedModel


class Attempt(TimeStampedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"
        SCORING = "scoring", "Scoring"
        SCORED = "scored", "Scored"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts"
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempts",
    )
    exam = models.ForeignKey(
        "catalog.Exam", on_delete=models.PROTECT, related_name="attempts"
    )
    pack = models.ForeignKey(
        "catalog.MockPack",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempts",
        help_text="Empty for ad-hoc question-wise practice.",
    )
    mode = models.CharField(max_length=20, choices=PracticeMode.choices)
    section_code = models.CharField(max_length=10, choices=Section.choices, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NOT_STARTED
    )
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    scored_at = models.DateTimeField(null=True, blank=True)
    server_deadline_at = models.DateTimeField(null=True, blank=True)
    duration_sec = models.PositiveIntegerField(null=True, blank=True)
    config_snapshot = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "status", "-started_at"],
                name="attempt_user_status_started",
            )
        ]

    def __str__(self):
        return f"{self.user} · {self.exam.code} · {self.mode} ({self.status})"


class AttemptItem(TimeStampedModel):
    class ScoreStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SCORED = "scored", "Scored"
        ERROR = "error", "Error"
        SKIPPED = "skipped", "Skipped"

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="items")
    order = models.PositiveIntegerField()
    question = models.ForeignKey(
        "catalog.Question", on_delete=models.PROTECT, related_name="attempt_items"
    )
    question_version = models.PositiveIntegerField(default=1)
    section_code = models.CharField(max_length=10, choices=Section.choices)
    stem_snapshot = models.JSONField(default=dict, blank=True)
    answer_key_snapshot = models.JSONField(
        default=dict, blank=True, help_text="Server only — exclude from serializers."
    )
    time_limit_sec = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    response = models.JSONField(null=True, blank=True)
    response_flags = models.JSONField(default=dict, blank=True)
    audio = models.ForeignKey(
        "catalog.Asset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempt_items",
        help_text="Student's speaking recording.",
    )
    score_status = models.CharField(
        max_length=10, choices=ScoreStatus.choices, default=ScoreStatus.PENDING
    )
    item_score = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["attempt", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "order"], name="uniq_attemptitem_attempt_order"
            )
        ]

    def __str__(self):
        return f"{self.attempt_id} #{self.order}"


class FeedbackNote(TimeStampedModel):
    attempt = models.ForeignKey(
        Attempt, on_delete=models.CASCADE, related_name="feedback_notes"
    )
    attempt_item = models.ForeignKey(
        AttemptItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feedback_notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedback_notes",
    )
    body = models.TextField()

    def __str__(self):
        return f"Feedback by {self.author} on {self.attempt_id}"


class QuestionExposure(models.Model):
    """Which questions a student has already been shown (no-repeat selection)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exposures"
    )
    question = models.ForeignKey(
        "catalog.Question", on_delete=models.CASCADE, related_name="exposures"
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField()
    times_seen = models.PositiveIntegerField(default=1)
    last_mode = models.CharField(max_length=20, choices=PracticeMode.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"], name="uniq_exposure_user_question"
            )
        ]
        indexes = [models.Index(fields=["user", "last_seen_at"])]

    def __str__(self):
        return f"{self.user} saw {self.question_id} ×{self.times_seen}"
