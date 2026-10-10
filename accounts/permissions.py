from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import Role
from .services import get_profile, home_url_for, sync_auth_context


class RoleRequiredMixin(LoginRequiredMixin):
    """Anonymous → login redirect; signed in without one of `roles` → 403."""

    roles = (Role.STUDENT, Role.ORG, Role.SUPER_ADMIN)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        context = getattr(request, "auth_context", None) or sync_auth_context(request)
        if context["role"] not in self.roles:
            return self.wrong_role(request, context)
        return super().dispatch(request, *args, **kwargs)

    def wrong_role(self, request, context):
        raise PermissionDenied


class StudentRequiredMixin(RoleRequiredMixin):
    """Students only; org/super admins go to their own home, new students onboard."""

    roles = (Role.STUDENT,)

    def wrong_role(self, request, context):
        return redirect(home_url_for(request.user, context))

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and get_profile(request.user).onboarded_at is None
        ):
            context = getattr(request, "auth_context", None) or sync_auth_context(
                request
            )
            if context["role"] == Role.STUDENT:
                return redirect("accounts:onboarding")
        return super().dispatch(request, *args, **kwargs)


class OrgRequiredMixin(RoleRequiredMixin):
    roles = (Role.ORG,)
