"""Content factory: sources → patterns → jobs → drafts → published questions."""

from django.conf import settings
from django.db import models

from catalog.models import Asset, Exam, Question, QuestionType, Stimulus
from core.models import TimeStampedModel


class SourceDocument(TimeStampedModel):
    """Reference material (practice book, sample test). Patterns only, never copied."""

    class Kind(models.TextChoices):
        PRACTICE_BOOK = "practice_book", "Practice book"
        OFFICIAL_SAMPLE = "official_sample", "Official sample"
        TEACHER_NOTES = "teacher_notes", "Teacher notes"
        PASTED_TEXT = "pasted_text", "Pasted text"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        EXTRACTED = "extracted", "Extracted"
        ANALYSED = "analysed", "Analysed"
        FAILED = "failed", "Failed"

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="sources")
    title = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.PRACTICE_BOOK
    )
    file = models.FileField(
        upload_to="sources/", blank=True, max_length=255, help_text="PDF, DOCX or TXT."
    )
    pasted_text = models.TextField(blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    page_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.UPLOADED
    )
    error = models.TextField(blank=True)
    licence_note = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_sources",
    )

    def __str__(self):
        return self.title


class SourcePage(models.Model):
    document = models.ForeignKey(
        SourceDocument, on_delete=models.CASCADE, related_name="pages"
    )
    page_no = models.PositiveIntegerField()
    text = models.TextField(blank=True)
    minhash = models.BinaryField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["document", "page_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "page_no"], name="uniq_sourcepage_doc_page"
            )
        ]

    def __str__(self):
        return f"{self.document} p{self.page_no}"


class PatternProfile(TimeStampedModel):
    """What the analyst agent learned about one question type from a source."""

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    document = models.ForeignKey(
        SourceDocument,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="patterns",
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="patterns")
    question_type = models.ForeignKey(
        QuestionType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="patterns",
        help_text="Empty = pattern the analyst could not map to an existing type.",
    )
    detected_label = models.CharField(max_length=200)
    spec = models.JSONField(default=dict, blank=True)
    page_refs = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PROPOSED
    )
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        code = self.question_type.code if self.question_type_id else "unmapped"
        return f"{code}: {self.detected_label}"


class GenerationJob(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        REVIEW = "review", "Ready for review"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class Target(models.TextChoices):
        PRACTICE = "practice", "Practice pool"
        MOCK = "mock", "Mock pool"

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="gen_jobs")
    question_type = models.ForeignKey(
        QuestionType, on_delete=models.CASCADE, related_name="gen_jobs"
    )
    count = models.PositiveSmallIntegerField(default=5)
    difficulty_mix = models.JSONField(
        default=dict, blank=True, help_text='e.g. {"2": 2, "3": 2, "4": 1}'
    )
    topic_hints = models.TextField(blank=True, help_text="One topic per line.")
    target_pool = models.CharField(
        max_length=10, choices=Target.choices, default=Target.PRACTICE
    )
    profiles = models.ManyToManyField(PatternProfile, blank=True, related_name="jobs")
    llm_model = models.CharField(
        max_length=100, blank=True, help_text="Empty = CONTENT_LLM_MODEL."
    )
    budget_usd = models.DecimalField(max_digits=8, decimal_places=2, default=5)
    spent_usd = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    tokens_in = models.PositiveIntegerField(default=0)
    tokens_out = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.QUEUED
    )
    error = models.TextField(blank=True)
    is_mock = models.BooleanField(
        default=False, help_text="Ran with mock providers (no real LLM)."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_jobs",
    )

    def __str__(self):
        return f"Job {self.pk}: {self.count}× {self.question_type}"


class JobStep(models.Model):
    """Per-step trace: what went in, what the LLM / provider returned."""

    class Agent(models.TextChoices):
        EXTRACT = "extract", "Extract"
        ANALYST = "analyst", "Analyst"
        PLANNER = "planner", "Planner"
        WRITER = "writer", "Writer"
        VALIDATE = "validate", "Validate"
        REVIEWER = "reviewer", "Reviewer"
        DEDUP = "dedup", "Dedup"
        MEDIA = "media", "Media"
        PUBLISH = "publish", "Publish"

    job = models.ForeignKey(
        GenerationJob,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="steps",
    )
    document = models.ForeignKey(
        SourceDocument,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="steps",
    )
    draft = models.ForeignKey(
        "DraftQuestion",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="steps",
    )
    agent = models.CharField(max_length=10, choices=Agent.choices)
    provider = models.CharField(max_length=40, blank=True)
    ok = models.BooleanField(default=True)
    input = models.JSONField(default=dict, blank=True)
    output = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    tokens_in = models.PositiveIntegerField(default=0)
    tokens_out = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.agent} ({'ok' if self.ok else 'error'})"


class QuestionBrief(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        DUPLICATE = "duplicate", "Duplicate (dropped)"
        WRITTEN = "written", "Written"
        FAILED = "failed", "Failed"

    job = models.ForeignKey(
        GenerationJob, on_delete=models.CASCADE, related_name="briefs"
    )
    topic = models.CharField(max_length=120)
    subtopic = models.CharField(max_length=120, blank=True)
    difficulty = models.PositiveSmallIntegerField(default=3)
    angle = models.CharField(max_length=300, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PLANNED
    )

    def __str__(self):
        return f"{self.topic} / {self.subtopic} (L{self.difficulty})"


class DraftQuestion(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFTED = "drafted", "Drafted"
        NEEDS_REVISION = "needs_revision", "Needs revision"
        MEDIA_PENDING = "media_pending", "Media pending"
        READY = "ready", "Ready for review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    class Verdict(models.TextChoices):
        UNIQUE = "unique", "Unique"
        SIMILAR = "similar", "Similar (check)"
        DUPLICATE = "duplicate", "Duplicate"
        COPY_RISK = "copy_risk", "Copy risk"

    job = models.ForeignKey(
        GenerationJob, on_delete=models.CASCADE, related_name="drafts"
    )
    brief = models.OneToOneField(
        QuestionBrief,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="draft",
    )
    question_type = models.ForeignKey(
        QuestionType, on_delete=models.CASCADE, related_name="drafts"
    )
    title = models.CharField(max_length=200)
    topic = models.CharField(max_length=120, blank=True)
    subtopic = models.CharField(max_length=120, blank=True)
    difficulty = models.PositiveSmallIntegerField(default=3)
    contract = models.JSONField(
        default=dict, blank=True, help_text="Raw writer output."
    )
    stimulus = models.JSONField(default=dict, blank=True)
    stem = models.JSONField(default=dict, blank=True)
    answer_key = models.JSONField(default=dict, blank=True)
    scorer_meta = models.JSONField(default=dict, blank=True)
    explanations = models.JSONField(default=dict, blank=True)
    validation = models.JSONField(default=dict, blank=True)
    review = models.JSONField(default=dict, blank=True)
    dedup = models.JSONField(default=dict, blank=True)
    verdict = models.CharField(
        max_length=10, choices=Verdict.choices, default=Verdict.UNIQUE
    )
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    minhash = models.BinaryField(null=True, blank=True, editable=False)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.DRAFTED
    )
    is_mock = models.BooleanField(default=False)
    admin_feedback = models.TextField(blank=True)
    revision_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revisions",
    )
    published_question = models.OneToOneField(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_draft",
    )
    published_stimulus = models.ForeignKey(
        Stimulus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_drafts",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class MediaRequest(TimeStampedModel):
    class Kind(models.TextChoices):
        AUDIO = "audio", "Audio (TTS)"
        CHART = "chart", "Chart (matplotlib)"
        IMAGE = "image", "Image (Gemini)"
        MAP = "map", "Map (image + label overlay)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    draft = models.ForeignKey(
        DraftQuestion, on_delete=models.CASCADE, related_name="media"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    role = models.CharField(
        max_length=20, choices=Asset.Role.choices, default=Asset.Role.STIMULUS_AUDIO
    )
    spec = models.JSONField(default=dict, blank=True)
    provider = models.CharField(max_length=30, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    asset = models.ForeignKey(
        Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    error = models.TextField(blank=True)

    def __str__(self):
        return f"{self.kind} for {self.draft}"


class SimilarityHit(models.Model):
    class Target(models.TextChoices):
        QUESTION = "question", "Question"
        DRAFT = "draft", "Draft"
        SOURCE = "source", "Source page"

    class Method(models.TextChoices):
        EXACT = "exact", "Exact hash"
        MINHASH = "minhash", "MinHash (lexical)"
        EMBEDDING = "embedding", "Embedding (semantic)"
        RUN = "run", "Copied word run"

    draft = models.ForeignKey(
        DraftQuestion, on_delete=models.CASCADE, related_name="similar"
    )
    target_type = models.CharField(max_length=10, choices=Target.choices)
    target_id = models.CharField(max_length=64)
    target_label = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=10, choices=Method.choices)
    score = models.FloatField()
    verdict = models.CharField(max_length=10, choices=DraftQuestion.Verdict.choices)

    class Meta:
        ordering = ["-score"]

    def __str__(self):
        return f"{self.method} {self.score:.2f} → {self.target_label}"


class Embedding(models.Model):
    """Vector store (float32 bytes). Brute-force cosine; pgvector later."""

    class Owner(models.TextChoices):
        QUESTION = "question", "Question"
        DRAFT = "draft", "Draft"
        BRIEF = "brief", "Brief"

    owner_type = models.CharField(max_length=10, choices=Owner.choices)
    owner_id = models.CharField(max_length=64)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="+")
    question_type = models.ForeignKey(
        QuestionType, on_delete=models.CASCADE, related_name="+"
    )
    model = models.CharField(max_length=60)
    dim = models.PositiveIntegerField()
    vector = models.BinaryField()
    text_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner_type", "owner_id", "model"], name="uniq_embedding_owner"
            )
        ]
        indexes = [models.Index(fields=["question_type", "owner_type", "model"])]

    def __str__(self):
        return f"{self.owner_type}:{self.owner_id} ({self.model})"


class CoverageTarget(models.Model):
    question_type = models.ForeignKey(
        QuestionType, on_delete=models.CASCADE, related_name="coverage_targets"
    )
    pool = models.CharField(
        max_length=10,
        choices=GenerationJob.Target.choices,
        default=GenerationJob.Target.PRACTICE,
    )
    min_active = models.PositiveIntegerField(default=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question_type", "pool"], name="uniq_coverage_type_pool"
            )
        ]

    def __str__(self):
        return f"{self.question_type} {self.pool} ≥ {self.min_active}"
