from django.contrib import admin

from .models import Attempt, AttemptItem, FeedbackNote, QuestionExposure


class AttemptItemInline(admin.TabularInline):
    model = AttemptItem
    extra = 0
    fields = [
        "order",
        "question",
        "section_code",
        "score_status",
        "item_score",
        "submitted_at",
    ]
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
    actions = ["rescore"]

    @admin.action(description="Re-score selected attempts (practice scoring)")
    def rescore(self, request, queryset):
        from scoring.services import score_attempt

        done = 0
        for attempt in queryset.exclude(
            status__in=[Attempt.Status.NOT_STARTED, Attempt.Status.IN_PROGRESS]
        ):
            done += score_attempt(attempt, force=True).status == Attempt.Status.SCORED
        self.message_user(request, f"Re-scored {done} attempt(s).")


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


@admin.register(QuestionExposure)
class QuestionExposureAdmin(admin.ModelAdmin):
    list_display = ["user", "question", "times_seen", "last_mode", "last_seen_at"]
    list_filter = ["last_mode"]
    search_fields = ["user__username", "question__title"]
    raw_id_fields = ["user", "question"]
