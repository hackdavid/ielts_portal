import json
from types import SimpleNamespace

from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Count, Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from attempts.rendering import build
from catalog.models import Question

from . import pipeline
from .models import (
    CoverageTarget,
    DraftQuestion,
    Embedding,
    GenerationJob,
    JobStep,
    MediaRequest,
    PatternProfile,
    QuestionBrief,
    SimilarityHit,
    SourceDocument,
    SourcePage,
)
from .publish import PublishError, blockers, publish


def _pretty(value):
    return format_html(
        '<pre style="white-space:pre-wrap;max-height:400px;overflow:auto">{}</pre>',
        json.dumps(value, indent=2, ensure_ascii=False, default=str),
    )


def _run(job):
    if settings.CONTENT_JOBS_INLINE:
        pipeline.start_in_background(job.pk)
        return "started in the background — refresh to follow progress"
    return "queued for `manage.py run_content_jobs`"


# ---------------------------------------------------------------- sources


class SourcePageInline(admin.TabularInline):
    model = SourcePage
    extra = 0
    fields = ["page_no", "preview"]
    readonly_fields = fields
    can_delete = False

    @admin.display(description="Text")
    def preview(self, obj):
        return obj.text[:300]


class PatternInline(admin.TabularInline):
    model = PatternProfile
    extra = 0
    fields = ["question_type", "detected_label", "status", "page_refs"]
    show_change_link = True


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "exam", "kind", "status", "page_count", "created_at"]
    list_filter = ["exam", "kind", "status"]
    search_fields = ["title"]
    readonly_fields = ["sha256", "page_count", "status", "error", "uploaded_by"]
    inlines = [PatternInline, SourcePageInline]
    actions = ["extract", "analyse"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
        if (
            not change
            or "file" in form.changed_data
            or "pasted_text" in form.changed_data
        ):
            pipeline.extract_document(obj)

    @admin.action(description="Extract text")
    def extract(self, request, queryset):
        for doc in queryset:
            pipeline.extract_document(doc)
        self.message_user(request, f"Extracted {queryset.count()} document(s).")

    @admin.action(description="Analyse question patterns (analyst agent)")
    def analyse(self, request, queryset):
        made = 0
        for doc in queryset:
            try:
                made += len(pipeline.analyse_document(doc))
            except Exception as exc:
                self.message_user(request, f"{doc}: {exc}", messages.ERROR)
        self.message_user(
            request, f"{made} pattern profile(s) proposed — approve them."
        )


@admin.register(SourcePage)
class SourcePageAdmin(admin.ModelAdmin):
    list_display = ["document", "page_no"]
    list_filter = ["document__exam"]
    search_fields = ["text", "document__title"]


@admin.register(PatternProfile)
class PatternProfileAdmin(admin.ModelAdmin):
    list_display = ["detected_label", "question_type", "exam", "status", "document"]
    list_filter = ["status", "exam", "question_type"]
    search_fields = ["detected_label"]
    actions = ["approve", "reject"]

    @admin.action(description="Approve")
    def approve(self, request, queryset):
        queryset.update(status=PatternProfile.Status.APPROVED)

    @admin.action(description="Reject")
    def reject(self, request, queryset):
        queryset.update(status=PatternProfile.Status.REJECTED)


# ---------------------------------------------------------------- jobs


class StepInline(admin.TabularInline):
    model = JobStep
    fk_name = "job"
    extra = 0
    fields = ["created_at", "agent", "provider", "ok", "latency_ms", "tokens", "trace"]
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    @admin.display(description="Tokens")
    def tokens(self, obj):
        return f"{obj.tokens_in}/{obj.tokens_out}"

    @admin.display(description="Error / output")
    def trace(self, obj):
        return obj.error[:200] if obj.error else json.dumps(obj.output)[:200]


class BriefInline(admin.TabularInline):
    model = QuestionBrief
    extra = 0
    fields = ["topic", "subtopic", "difficulty", "angle", "status"]


class DraftInline(admin.TabularInline):
    model = DraftQuestion
    fk_name = "job"
    extra = 0
    fields = ["title", "status", "verdict", "is_mock"]
    readonly_fields = fields
    show_change_link = True
    can_delete = False


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "question_type",
        "count",
        "target_pool",
        "status",
        "is_mock",
        "draft_count",
        "spent_usd",
        "created_at",
    ]
    list_filter = ["status", "exam", "target_pool", "is_mock"]
    autocomplete_fields = ["question_type"]
    filter_horizontal = ["profiles"]
    readonly_fields = [
        "status",
        "error",
        "is_mock",
        "spent_usd",
        "tokens_in",
        "tokens_out",
        "created_by",
    ]
    inlines = [BriefInline, DraftInline, StepInline]
    actions = ["run_now"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_drafts=Count("drafts"))

    @admin.display(description="Drafts", ordering="_drafts")
    def draft_count(self, obj):
        return obj._drafts

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        if obj.question_type_id:
            obj.exam = obj.question_type.exam
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(request, f"Job {obj.pk} {_run(obj)}.")
        return super().response_add(request, obj, post_url_continue)

    def get_changeform_initial_data(self, request):
        return {"difficulty_mix": {"2": 1, "3": 2, "4": 2}}

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "exam" in form.base_fields:
            form.base_fields["exam"].required = False
            form.base_fields["exam"].help_text = "Taken from the question type."
        return form

    @admin.action(description="Run / resume selected jobs")
    def run_now(self, request, queryset):
        for job in queryset.exclude(status=GenerationJob.Status.RUNNING):
            job.status = GenerationJob.Status.QUEUED
            job.save(update_fields=["status"])
            self.message_user(request, f"Job {job.pk} {_run(job)}.")


@admin.register(JobStep)
class JobStepAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "agent",
        "job",
        "draft",
        "provider",
        "ok",
        "latency_ms",
    ]
    list_filter = ["agent", "ok"]
    readonly_fields = [
        "job",
        "document",
        "draft",
        "agent",
        "provider",
        "ok",
        "error",
        "tokens_in",
        "tokens_out",
        "latency_ms",
        "input_pretty",
        "output_pretty",
    ]
    exclude = ["input", "output"]

    @admin.display(description="Input")
    def input_pretty(self, obj):
        return _pretty(obj.input)

    @admin.display(description="Output")
    def output_pretty(self, obj):
        return _pretty(obj.output)


@admin.register(QuestionBrief)
class QuestionBriefAdmin(admin.ModelAdmin):
    list_display = ["topic", "subtopic", "difficulty", "status", "job"]
    list_filter = ["status"]
    search_fields = ["topic", "subtopic"]


# ---------------------------------------------------------------- drafts


class MediaInline(admin.TabularInline):
    model = MediaRequest
    extra = 0
    fields = ["kind", "status", "provider", "asset", "attempts", "error"]
    readonly_fields = fields
    can_delete = False


class SimilarInline(admin.TabularInline):
    model = SimilarityHit
    extra = 0
    fields = ["method", "score", "verdict", "target_type", "target_label"]
    readonly_fields = fields
    can_delete = False


def _hit_url(hit):
    if hit.target_type == "question":
        return reverse("admin:catalog_question_change", args=[hit.target_id])
    if hit.target_type == "draft":
        return reverse("admin:content_draftquestion_change", args=[hit.target_id])
    return reverse("admin:content_sourcepage_change", args=[hit.target_id])


@admin.register(DraftQuestion)
class DraftQuestionAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "question_type",
        "status",
        "verdict",
        "agreement",
        "has_media",
        "is_mock",
        "created_at",
    ]
    list_filter = [
        "status",
        "verdict",
        "is_mock",
        "question_type__exam",
        "question_type",
    ]
    search_fields = ["title", "topic", "subtopic"]
    readonly_fields = [
        "preview",
        "job",
        "question_type",
        "status",
        "verdict",
        "is_mock",
        "published_question",
        "published_stimulus",
        "revision_of",
        "validation_pretty",
        "review_pretty",
        "contract_pretty",
    ]
    fields = [
        "preview",
        "title",
        "topic",
        "subtopic",
        "difficulty",
        "admin_feedback",
        "job",
        "question_type",
        "status",
        "verdict",
        "is_mock",
        "published_question",
        "published_stimulus",
        "revision_of",
        "stem",
        "answer_key",
        "explanations",
        "validation_pretty",
        "review_pretty",
        "contract_pretty",
    ]
    inlines = [MediaInline, SimilarInline]
    actions = ["publish_selected", "force_publish", "reject", "revise", "redo_media"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("question_type", "job")

    @admin.display(description="Agreement")
    def agreement(self, obj):
        value = obj.review.get("agreement")
        return "–" if value is None else f"{value:.0%}"

    @admin.display(description="Media", boolean=True)
    def has_media(self, obj):
        return obj.media.filter(status=MediaRequest.Status.DONE).exists()

    @admin.display(description="Validation")
    def validation_pretty(self, obj):
        return _pretty(obj.validation)

    @admin.display(description="Review")
    def review_pretty(self, obj):
        return _pretty(obj.review)

    @admin.display(description="Raw writer output")
    def contract_pretty(self, obj):
        return _pretty(obj.contract)

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj.pk:
            return "-"
        media = {m.kind: m.asset_id for m in obj.media.filter(status="done")}
        image = media.get("chart") or media.get("map") or media.get("image")
        stem = {
            **obj.stem,
            "_engine": obj.question_type.engine,
            "_audio_asset": str(media["audio"]) if media.get("audio") else None,
            "_image_asset": str(image) if image else None,
        }
        view = build(
            SimpleNamespace(stem_snapshot=stem, response={}, order=1, audio_id=None)
        )
        hits = list(obj.similar.all()[:10])
        for h in hits:
            h.url = _hit_url(h)
        return mark_safe(  # noqa: S308 - template auto-escapes
            render_to_string(
                "admin/content/draft_preview.html",
                {
                    "view": view,
                    "is_mock": obj.is_mock,
                    "answer_key": json.dumps(obj.answer_key, indent=1),
                    "explanations": json.dumps(obj.explanations, indent=1)
                    if any(
                        (v or {}).get("why") or (v or {}).get("evidence")
                        for v in obj.explanations.values()
                    )
                    else "",
                    "transcript": obj.scorer_meta.get("transcript", ""),
                    "issues": obj.validation.get("issues", []),
                    "review": obj.review,
                    "verdict": obj.get_verdict_display(),
                    "hits": hits,
                    "blockers": blockers(obj),
                },
            )
        )

    def _publish(self, request, queryset, force):
        done = 0
        for draft in queryset:
            try:
                publish(draft, request.user, force=force)
                done += 1
            except PublishError as exc:
                self.message_user(request, f"{draft}: {exc}", messages.WARNING)
        if done:
            self.message_user(request, f"Published {done} question(s).")

    @admin.action(description="Publish to question bank")
    def publish_selected(self, request, queryset):
        self._publish(request, queryset, force=False)

    @admin.action(description="Publish anyway (override dedup / reviewer)")
    def force_publish(self, request, queryset):
        self._publish(request, queryset, force=True)

    @admin.action(description="Reject")
    def reject(self, request, queryset):
        queryset.exclude(status=DraftQuestion.Status.PUBLISHED).update(
            status=DraftQuestion.Status.REJECTED
        )

    @admin.action(description="Revise (re-write with feedback)")
    def revise(self, request, queryset):
        for draft in queryset.exclude(status=DraftQuestion.Status.PUBLISHED):
            try:
                new = pipeline.revise(draft)
                self.message_user(request, f"Revised → {new}.")
            except Exception as exc:
                self.message_user(request, f"{draft}: {exc}", messages.ERROR)

    @admin.action(description="Re-generate media")
    def redo_media(self, request, queryset):
        for draft in queryset.exclude(status=DraftQuestion.Status.PUBLISHED):
            draft.media.all().delete()
            pipeline.plan_media(draft)
            pipeline.make_media(draft)
        self.message_user(request, "Media regenerated.")


@admin.register(MediaRequest)
class MediaRequestAdmin(admin.ModelAdmin):
    list_display = ["draft", "kind", "status", "provider", "asset", "attempts"]
    list_filter = ["kind", "status", "provider"]


@admin.register(SimilarityHit)
class SimilarityHitAdmin(admin.ModelAdmin):
    list_display = ["draft", "method", "score", "verdict", "target_label"]
    list_filter = ["method", "verdict", "target_type"]


@admin.register(Embedding)
class EmbeddingAdmin(admin.ModelAdmin):
    list_display = ["owner_type", "owner_id", "question_type", "model", "dim"]
    list_filter = ["owner_type", "model"]
    exclude = ["vector"]


@admin.register(CoverageTarget)
class CoverageTargetAdmin(admin.ModelAdmin):
    list_display = ["question_type", "pool", "min_active", "active", "deficit"]
    list_filter = ["pool", "question_type__exam"]
    list_editable = ["min_active"]
    autocomplete_fields = ["question_type"]
    actions = ["queue_jobs"]

    def _active(self, obj):
        pools = (
            Question.PRACTICE_POOLS if obj.pool == "practice" else Question.MOCK_POOLS
        )
        return Question.objects.filter(
            Q(question_type=obj.question_type) & Q(pool__in=pools), is_active=True
        ).count()

    @admin.display(description="Active questions")
    def active(self, obj):
        return self._active(obj)

    @admin.display(description="Deficit")
    def deficit(self, obj):
        return max(obj.min_active - self._active(obj), 0)

    @admin.action(description="Create generation jobs for the deficit")
    def queue_jobs(self, request, queryset):
        for target in queryset:
            need = min(self.deficit(target), 10)
            if need:
                job = GenerationJob.objects.create(
                    exam=target.question_type.exam,
                    question_type=target.question_type,
                    count=need,
                    target_pool=target.pool,
                    created_by=request.user,
                )
                self.message_user(request, f"Job {job.pk} {_run(job)}.")
