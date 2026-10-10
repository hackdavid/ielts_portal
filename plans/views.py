from django.views.generic import TemplateView

from accounts.permissions import RoleRequiredMixin


class LockedView(RoleRequiredMixin, TemplateView):
    template_name = "plans/locked.html"
