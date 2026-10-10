from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    autocomplete_fields = ["primary_exam"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "display_name",
        "role_primary",
        "primary_exam",
        "target_score",
    ]
    list_filter = ["role_primary", "primary_exam"]
    search_fields = ["user__username", "user__email", "display_name"]
    autocomplete_fields = ["user", "primary_exam"]
