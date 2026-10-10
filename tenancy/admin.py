from django.contrib import admin

from .models import AccessInvite, Membership, Tenant


class AccessInviteInline(admin.TabularInline):
    model = AccessInvite
    extra = 1
    fields = ["email", "role", "is_active", "accepted_by", "accepted_at"]
    readonly_fields = ["accepted_by", "accepted_at"]
    verbose_name = "Access email"
    verbose_name_plural = "Access emails (org admins and students allowed to sign in)"


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
    inlines = [AccessInviteInline, MembershipInline]


@admin.register(AccessInvite)
class AccessInviteAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "tenant",
        "role",
        "is_active",
        "accepted_by",
        "accepted_at",
    ]
    list_filter = ["role", "is_active", "tenant"]
    search_fields = ["email", "tenant__name"]
    autocomplete_fields = ["tenant"]
    readonly_fields = ["accepted_by", "accepted_at"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "tenant", "role", "is_active", "joined_at"]
    list_filter = ["role", "is_active", "tenant"]
    search_fields = ["user__username", "user__email", "tenant__name"]
    autocomplete_fields = ["tenant", "user"]
