from django.views.generic import TemplateView

from accounts.permissions import StudentRequiredMixin
from accounts.services import get_profile


class DashboardView(StudentRequiredMixin, TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = get_profile(self.request.user)
        return context
