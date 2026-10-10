from django.views.generic import TemplateView

from accounts.permissions import OrgRequiredMixin
from tenancy.models import AccessInvite, Membership, Tenant


class ConsoleView(OrgRequiredMixin, TemplateView):
    template_name = "institute/console.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = Tenant.objects.get(pk=self.request.auth_context["tenant_id"])
        members = (
            Membership.objects.filter(tenant=tenant, is_active=True)
            .select_related("user__profile")
            .order_by("role", "user__email")
        )
        context.update(
            tenant=tenant,
            members=members,
            student_count=sum(m.role == Membership.Role.STUDENT for m in members),
            pending_invites=AccessInvite.objects.filter(
                tenant=tenant, is_active=True, accepted_at__isnull=True
            ).order_by("email"),
        )
        return context
