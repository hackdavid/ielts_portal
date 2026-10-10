from django.contrib import admin

from .models import ScoreBreakdown, ScoringConfig


@admin.register(ScoreBreakdown)
class ScoreBreakdownAdmin(admin.ModelAdmin):
    list_display = ["attempt", "overall", "scale", "config_version", "created_at"]
    list_filter = ["scale"]
    search_fields = ["attempt__id", "attempt__user__username"]
    autocomplete_fields = ["attempt"]


@admin.register(ScoringConfig)
class ScoringConfigAdmin(admin.ModelAdmin):
    list_display = ["exam", "tenant", "version", "is_active", "created_at"]
    list_filter = ["exam", "is_active"]
    search_fields = ["version", "notes"]
    autocomplete_fields = ["exam", "tenant"]
