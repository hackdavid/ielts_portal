from django.contrib import admin

from .models import Membership, Tenant


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ["user"]


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "is_active",
        "custom_domain",
        "seat_limit",
        "created_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "custom_domain"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "tenant", "role", "is_active", "joined_at"]
    list_filter = ["role", "is_active", "tenant"]
    search_fields = ["user__username", "user__email", "tenant__name"]
    autocomplete_fields = ["tenant", "user"]
