import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel


class Section(models.TextChoices):
    SPEAKING = "speaking", "Speaking"
    WRITING = "writing", "Writing"
    READING = "reading", "Reading"
    LISTENING = "listening", "Listening"
    MIXED = "mixed", "Mixed"


class PracticeMode(models.TextChoices):
    FULL_MOCK = "full_mock", "Full mock"
    SECTION = "section", "Section-wise"
    QUESTION = "question", "Question-wise"


class Exam(TimeStampedModel):
    class Kind(models.TextChoices):
        PTE = "pte", "PTE"
        IELTS = "ielts", "IELTS"
        OTHER = "other", "Other"

    code = models.CharField(max_length=32, unique=True, help_text="e.g. PTE_ACADEMIC")
    slug = models.SlugField(unique=True, help_text="URL slug, e.g. pte-academic")
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    default_config = models.JSONField(
        default=dict, blank=True, help_text="Timers, navigation policy, ui_variant."
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class QuestionType(TimeStampedModel):
    class Engine(models.TextChoices):
        MCQ_SINGLE = "mcq_single", "MCQ single"
        MCQ_MULTI = "mcq_multi", "MCQ multi"
        FIB_DROPDOWN = "fib_dropdown", "FIB dropdown"
        FIB_DRAG = "fib_drag", "FIB drag-drop / bank"
        FIB_TEXT = "fib_text", "FIB type-in"
        REORDER = "reorder", "Reorder paragraphs"
        HIW = "hiw", "Highlight incorrect words"
        MATCHING = "matching", "Matching"
        TFNG = "tfng", "TFNG / YNNG"
        COMPLETION = "completion", "Form / note / table completion"
        MAP_LABEL = "map_label", "Map / plan / diagram label"
        DICTATION = "dictation", "Write from dictation"
        WRITING_TEXT = "writing_text", "Writing (free text)"
        SPEAKING_AUDIO = "speaking_audio", "Speaking (audio)"

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="question_types"
    )
    code = models.CharField(
        max_length=32, help_text="e.g. RA, RS, FIB_DROP, TFNG, TASK2"
    )
    name = models.CharField(max_length=200)
    section = models.CharField(max_length=10, choices=Section.choices)
    engine = models.CharField(max_length=20, choices=Engine.choices)
    default_time_sec = models.PositiveIntegerField(null=True, blank=True)
    ui_schema = models.JSONField(default=dict, blank=True)
    scoring_schema = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["exam", "section", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "code"], name="uniq_qtype_exam_code"
            )
        ]

    def __str__(self):
        return f"{self.exam.code}:{self.code}"


class Tag(models.Model):
    class Kind(models.TextChoices):
        TOPIC = "topic", "Topic"
        PREDICTION = "prediction", "Prediction"
        SKILL = "skill", "Skill"

    slug = models.SlugField(unique=True)
    label = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.TOPIC)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


class Asset(models.Model):
    class Kind(models.TextChoices):
        AUDIO = "audio", "Audio"
        IMAGE = "image", "Image"
        PDF = "pdf", "PDF"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assets",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    file = models.FileField(upload_to="assets/%Y/%m/")
    content_type = models.CharField(max_length=100, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind}:{self.file.name}"


class Question(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    question_type = models.ForeignKey(
        QuestionType, on_delete=models.PROTECT, related_name="questions"
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="questions",
        help_text="Empty = global bank.",
    )
    title = models.CharField(max_length=200, help_text="Internal only.")
    difficulty = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="questions")
    is_prediction = models.BooleanField(default=False)
    stem = models.JSONField(default=dict, blank=True)
    answer_key = models.JSONField(
        default=dict, blank=True, help_text="Server only — never send to the player."
    )
    scorer_meta = models.JSONField(default=dict, blank=True)
    assets = models.ManyToManyField(Asset, blank=True, related_name="questions")
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(
                fields=["exam", "question_type", "is_active", "is_prediction"]
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if (
            self.question_type_id
            and self.exam_id
            and self.question_type.exam_id != self.exam_id
        ):
            raise ValidationError(
                {"question_type": "Question type belongs to a different exam."}
            )


class MockPack(TimeStampedModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="mock_packs")
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mock_packs",
    )
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    mode_default = models.CharField(
        max_length=20, choices=PracticeMode.choices, default=PracticeMode.FULL_MOCK
    )
    is_free = models.BooleanField(default=False)
    duration_sec = models.PositiveIntegerField(null=True, blank=True)
    structure = models.JSONField(default=list, blank=True)
    navigation_policy = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "slug"], name="uniq_mockpack_exam_slug"
            )
        ]

    def __str__(self):
        return self.title


class MockPackItem(models.Model):
    pack = models.ForeignKey(MockPack, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="pack_items"
    )
    order = models.PositiveIntegerField()
    section_code = models.CharField(max_length=10, choices=Section.choices)
    time_override_sec = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["pack", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["pack", "order"], name="uniq_mockpackitem_pack_order"
            )
        ]

    def __str__(self):
        return f"{self.pack} #{self.order}"


class StudyAid(TimeStampedModel):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_aids",
    )
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    body_html = models.TextField(blank=True, help_text="Sanitise before rendering.")
    tags = models.ManyToManyField(Tag, blank=True, related_name="study_aids")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
