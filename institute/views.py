from django.views.generic import TemplateView

from accounts.permissions import InstituteAdminRequiredMixin


class ConsoleView(InstituteAdminRequiredMixin, TemplateView):
    template_name = "institute/console.html"
