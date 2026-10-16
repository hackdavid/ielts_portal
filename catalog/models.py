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


class SectionTiming(models.Model):
    """Default (real-exam) timing per section; edit in admin under the Exam."""

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="section_timings"
    )
    section = models.CharField(max_length=10, choices=Section.choices)
    order = models.PositiveSmallIntegerField(default=0)
    duration_sec = models.PositiveIntegerField()
    extra_sec = models.PositiveIntegerField(
        default=0, help_text="Transfer / review time added after the section."
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["exam", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "section"], name="uniq_sectiontiming_exam_section"
            )
        ]

    def __str__(self):
        return f"{self.exam.code}:{self.section} {self.duration_sec}s"


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
    content_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON Schema of the generation contract (content.contracts).",
    )
    media_policy = models.JSONField(
        default=dict,
        blank=True,
        help_text='Media the type needs, e.g. {"stimulus": "audio", "voices": 2}.',
    )

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

    class Role(models.TextChoices):
        STIMULUS_AUDIO = "stimulus_audio", "Stimulus audio"
        STIMULUS_IMAGE = "stimulus_image", "Stimulus image"
        SOURCE_DOC = "source_doc", "Source document"
        RECORDING = "recording", "Student recording"
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
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OTHER)
    file = models.FileField(upload_to="assets/%Y/%m/", max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    provider = models.CharField(
        max_length=30, blank=True, help_text="upload, piper, matplotlib, gemini, mock…"
    )
    model_name = models.CharField(max_length=100, blank=True)
    prompt = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind}:{self.file.name}"


class Stimulus(TimeStampedModel):
    """Shared material (passage, listening script, image) behind question sets."""

    class Kind(models.TextChoices):
        READING_PASSAGE = "reading_passage", "Reading passage"
        LISTENING_SCRIPT = "listening_script", "Listening script"
        IMAGE = "image", "Image / chart"
        SPEAKING_CUE = "speaking_cue", "Speaking cue"
        WRITING_PROMPT = "writing_prompt", "Writing prompt"
        TEXT = "text", "Text snippet"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="stimuli")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, help_text="Passage text or full script.")
    script = models.JSONField(
        default=list, blank=True, help_text='Listening turns: [{"speaker", "text"}].'
    )
    meta = models.JSONField(default=dict, blank=True)
    audio = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audio_stimuli",
    )
    image = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="image_stimuli",
    )
    topic = models.ForeignKey(
        Tag, on_delete=models.SET_NULL, null=True, blank=True, related_name="stimuli"
    )
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        verbose_name_plural = "stimuli"

    def __str__(self):
        return self.title


class Question(TimeStampedModel):
    class Origin(models.TextChoices):
        SEED = "seed", "Seed"
        MANUAL = "manual", "Manual"
        GENERATED = "generated", "Generated"
        IMPORTED = "imported", "Imported"

    class Pool(models.TextChoices):
        PRACTICE = "practice", "Practice only"
        MOCK = "mock", "Mock only"
        BOTH = "both", "Practice and mock (legacy)"

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
    audio = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listening_questions",
        help_text="Listening recording played in the attempt player.",
    )
    stimulus = models.ForeignKey(
        Stimulus,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="questions",
        help_text="Shared passage / script / image (optional).",
    )
    explanations = models.JSONField(
        default=dict, blank=True, help_text="Per-item rationale (server only)."
    )
    origin = models.CharField(
        max_length=10, choices=Origin.choices, default=Origin.MANUAL
    )
    pool = models.CharField(
        max_length=10,
        choices=Pool.choices,
        default=Pool.BOTH,
        help_text="Practice questions never appear in mocks and vice versa.",
    )
    topic = models.ForeignKey(
        Tag,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_questions",
    )
    subtopic = models.CharField(max_length=120, blank=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    minhash = models.BinaryField(null=True, blank=True, editable=False)
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    PRACTICE_POOLS = (Pool.PRACTICE, Pool.BOTH)
    MOCK_POOLS = (Pool.MOCK, Pool.BOTH)

    class Meta:
        indexes = [
            models.Index(
                fields=["exam", "question_type", "is_active", "is_prediction"]
            ),
            models.Index(fields=["exam", "question_type", "pool", "is_active"]),
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
        if self.stimulus_id and self.exam_id and self.stimulus.exam_id != self.exam_id:
            raise ValidationError({"stimulus": "Stimulus belongs to a different exam."})


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

    def section_plan(self):
        """Effective timing per section: pack override, else exam default."""
        defaults = {t.section: t for t in self.exam.section_timings.all()}
        overrides = list(self.sections.all())
        if overrides:
            pairs = [(s.section, s.duration_sec) for s in overrides]
        else:
            pairs = [(section, None) for section in defaults]
        plan = []
        for section, override in pairs:
            default = defaults.get(section)
            plan.append(
                {
                    "section": section,
                    "duration_sec": override
                    or (default.duration_sec if default else 0),
                    "extra_sec": default.extra_sec if default else 0,
                    "is_override": bool(override),
                }
            )
        return plan


class MockPackSection(models.Model):
    """Optional per-mock section order/timing override."""

    pack = models.ForeignKey(
        MockPack, on_delete=models.CASCADE, related_name="sections"
    )
    section = models.CharField(max_length=10, choices=Section.choices)
    order = models.PositiveSmallIntegerField(default=0)
    duration_sec = models.PositiveIntegerField(
        null=True, blank=True, help_text="Empty = exam default timing."
    )

    class Meta:
        ordering = ["pack", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["pack", "section"], name="uniq_mockpacksection_pack_section"
            )
        ]

    def __str__(self):
        return f"{self.pack} · {self.section}"


class MockPackItem(models.Model):
    pack = models.ForeignKey(MockPack, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="pack_items"
    )
    order = models.PositiveIntegerField()
    section_code = models.CharField(max_length=10, choices=Section.choices)
    part = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Listening part / reading passage / writing task / speaking part.",
    )
    time_override_sec = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["pack", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["pack", "order"], name="uniq_mockpackitem_pack_order"
            ),
            models.UniqueConstraint(
                fields=["question"], name="uniq_mockpackitem_question"
            ),
        ]

    def __str__(self):
        return f"{self.pack} #{self.order}"

    def clean(self):
        if not self.question_id:
            return
        if self.question.pool == Question.Pool.PRACTICE:
            raise ValidationError(
                {"question": "Practice-only questions cannot be used in a mock."}
            )
        clash = MockPackItem.objects.filter(question_id=self.question_id)
        if self.pk:
            clash = clash.exclude(pk=self.pk)
        if pack := clash.select_related("pack").first():
            raise ValidationError(
                {"question": f"Already used in mock pack “{pack.pack}”."}
            )


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
