from django.contrib import admin

from .models import Attempt, AttemptItem, FeedbackNote


class AttemptItemInline(admin.TabularInline):
    model = AttemptItem
    extra = 0
    fields = ["order", "question", "section_code", "score_status", "submitted_at"]
    readonly_fields = fields
    show_change_link = True
    can_delete = False


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "exam",
        "mode",
        "status",
        "started_at",
        "submitted_at",
    ]
    list_filter = ["status", "mode", "exam"]
    search_fields = ["id", "user__username", "user__email"]
    autocomplete_fields = ["user", "tenant", "pack"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    inlines = [AttemptItemInline]


@admin.register(AttemptItem)
class AttemptItemAdmin(admin.ModelAdmin):
    list_display = ["attempt", "order", "question", "section_code", "score_status"]
    list_filter = ["score_status", "section_code"]
    search_fields = ["attempt__id", "question__title"]
    autocomplete_fields = ["attempt", "question"]


@admin.register(FeedbackNote)
class FeedbackNoteAdmin(admin.ModelAdmin):
    list_display = ["attempt", "attempt_item", "author", "created_at"]
    search_fields = ["body", "author__username"]
    autocomplete_fields = ["attempt", "attempt_item", "author"]
