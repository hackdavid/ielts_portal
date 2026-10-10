from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .services import get_profile, is_institute_admin, is_super_admin


class RoleRequiredMixin(LoginRequiredMixin):
    """Anonymous → login redirect; signed in without the role → 403."""

    def has_role(self, user):
        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.has_role(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin(RoleRequiredMixin):
    """Any signed-in user; sends not-yet-onboarded users to onboarding."""

    def has_role(self, user):
        return True

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and get_profile(request.user).onboarded_at is None
        ):
            return redirect("accounts:onboarding")
        return super().dispatch(request, *args, **kwargs)


class InstituteAdminRequiredMixin(RoleRequiredMixin):
    def has_role(self, user):
        return is_institute_admin(user) or is_super_admin(user)


class SuperAdminRequiredMixin(RoleRequiredMixin):
    def has_role(self, user):
        return is_super_admin(user)
