from django.contrib import admin

from .models import Entitlement, Plan, PlanDay, PlanDayProgress, PlanEnrolment


class PlanDayInline(admin.TabularInline):
    model = PlanDay
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "exam",
        "days_count",
        "price_stub",
        "is_active",
        "tenant",
    ]
    list_filter = ["exam", "is_active", "tenant"]
    search_fields = ["name", "code"]
    inlines = [PlanDayInline]


@admin.register(PlanDay)
class PlanDayAdmin(admin.ModelAdmin):
    list_display = ["plan", "day_index", "title"]
    list_filter = ["plan"]
    search_fields = ["title"]


class PlanDayProgressInline(admin.TabularInline):
    model = PlanDayProgress
    extra = 0


@admin.register(PlanEnrolment)
class PlanEnrolmentAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "started_on", "status"]
    list_filter = ["status", "plan"]
    search_fields = ["user__username", "plan__name"]
    autocomplete_fields = ["user", "plan"]
    inlines = [PlanDayProgressInline]


@admin.register(PlanDayProgress)
class PlanDayProgressAdmin(admin.ModelAdmin):
    list_display = ["enrolment", "day_index", "is_done"]
    list_filter = ["is_done"]


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ["key", "user", "tenant", "source", "expires_at"]
    list_filter = ["source", "tenant"]
    search_fields = ["key", "user__username"]
    autocomplete_fields = ["user", "tenant"]
