from django.contrib import admin

from .models import (
    Asset,
    Exam,
    MockPack,
    MockPackItem,
    MockPackSection,
    Question,
    QuestionType,
    SectionTiming,
    Stimulus,
    StudyAid,
    Tag,
)


class SectionTimingInline(admin.TabularInline):
    model = SectionTiming
    extra = 0
    verbose_name_plural = "Section timings (real-exam defaults)"


class MockPackSectionInline(admin.TabularInline):
    model = MockPackSection
    extra = 0
    verbose_name_plural = "Section order / timing overrides (empty = exam default)"


@admin.register(SectionTiming)
class SectionTimingAdmin(admin.ModelAdmin):
    list_display = ["exam", "section", "order", "duration_sec", "extra_sec"]
    list_filter = ["exam"]


@admin.register(MockPackSection)
class MockPackSectionAdmin(admin.ModelAdmin):
    list_display = ["pack", "section", "order", "duration_sec"]
    list_filter = ["pack__exam"]


class QuestionTypeInline(admin.TabularInline):
    model = QuestionType
    extra = 0
    fields = ["code", "name", "section", "engine", "default_time_sec"]
    show_change_link = True


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "kind", "is_active"]
    list_filter = ["kind", "is_active"]
    search_fields = ["name", "code"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [SectionTimingInline, QuestionTypeInline]


@admin.register(QuestionType)
class QuestionTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "exam", "section", "engine", "default_time_sec"]
    list_filter = ["exam", "section", "engine"]
    search_fields = ["code", "name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["label", "slug", "kind"]
    list_filter = ["kind"]
    search_fields = ["label", "slug"]
    prepopulated_fields = {"slug": ["label"]}


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "kind",
        "role",
        "provider",
        "file",
        "content_type",
        "duration_ms",
        "tenant",
        "created_at",
    ]
    list_filter = ["kind", "tenant"]
    search_fields = ["file", "content_type"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "exam",
        "question_type",
        "difficulty",
        "pool",
        "origin",
        "is_prediction",
        "is_active",
        "version",
        "tenant",
    ]
    list_filter = [
        "exam",
        "question_type__section",
        "pool",
        "origin",
        "is_prediction",
        "is_active",
        "difficulty",
    ]
    search_fields = ["title"]
    autocomplete_fields = [
        "question_type",
        "tenant",
        "tags",
        "assets",
        "audio",
        "stimulus",
        "topic",
    ]
    readonly_fields = ["id", "content_hash", "created_at", "updated_at"]


class MockPackItemInline(admin.TabularInline):
    model = MockPackItem
    extra = 0
    autocomplete_fields = ["question"]


@admin.register(MockPack)
class MockPackAdmin(admin.ModelAdmin):
    list_display = ["title", "exam", "mode_default", "is_free", "is_active", "tenant"]
    list_filter = ["exam", "mode_default", "is_free", "is_active"]
    search_fields = ["title", "slug"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [MockPackSectionInline, MockPackItemInline]


@admin.register(StudyAid)
class StudyAidAdmin(admin.ModelAdmin):
    list_display = ["title", "exam", "is_active", "updated_at"]
    list_filter = ["exam", "is_active"]
    search_fields = ["title", "slug"]
    prepopulated_fields = {"slug": ["title"]}
    autocomplete_fields = ["tags"]


@admin.register(MockPackItem)
class MockPackItemAdmin(admin.ModelAdmin):
    list_display = ["pack", "order", "question", "section_code", "time_override_sec"]
    list_filter = ["pack__exam", "section_code"]
    search_fields = ["pack__title", "question__title"]
    autocomplete_fields = ["pack", "question"]


@admin.register(Stimulus)
class StimulusAdmin(admin.ModelAdmin):
    list_display = ["title", "exam", "kind", "audio", "image", "created_at"]
    list_filter = ["exam", "kind"]
    search_fields = ["title", "body"]
    autocomplete_fields = ["audio", "image", "topic"]
    readonly_fields = ["id", "content_hash", "created_at", "updated_at"]
