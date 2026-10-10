from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from accounts.permissions import OrgRequiredMixin
from attempts.models import Attempt
from tenancy.models import AccessInvite, Membership, Tenant


class OrgMixin(OrgRequiredMixin):
    def get_tenant(self):
        return Tenant.objects.get(pk=self.request.auth_context["tenant_id"])


def student_members(tenant):
    return (
        Membership.objects.filter(
            tenant=tenant, is_active=True, role=Membership.Role.STUDENT
        )
        .select_related("user__profile__primary_exam")
        .annotate(
            attempt_count=Count("user__attempts", distinct=True),
            scored_count=Count(
                "user__attempts",
                filter=Q(user__attempts__status=Attempt.Status.SCORED),
                distinct=True,
            ),
            last_active=Max("user__attempts__started_at"),
        )
        .order_by("user__email")
    )


def pending_invites(tenant):
    return AccessInvite.objects.filter(
        tenant=tenant, is_active=True, accepted_at__isnull=True
    ).order_by("email")


def recent_scored(user_ids, limit):
    return (
        Attempt.objects.filter(user_id__in=user_ids, status=Attempt.Status.SCORED)
        .select_related("user__profile", "exam", "pack", "score_breakdown")
        .order_by("-submitted_at")[:limit]
    )


class ConsoleView(OrgMixin, TemplateView):
    template_name = "institute/console.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        students = list(student_members(tenant))
        members = (
            Membership.objects.filter(tenant=tenant, is_active=True)
            .select_related("user__profile")
            .order_by("role", "user__email")
        )
        context.update(
            tenant=tenant,
            members=members,
            students=students[:6],
            student_count=len(students),
            active_count=sum(1 for s in students if s.attempt_count),
            scored_total=sum(s.scored_count for s in students),
            pending_invites=pending_invites(tenant),
            recent=recent_scored([s.user_id for s in students], 6),
        )
        return context


class StudentsView(OrgMixin, TemplateView):
    template_name = "institute/students.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        students = student_members(tenant)
        query = self.request.GET.get("q", "").strip()
        if query:
            students = students.filter(
                Q(user__email__icontains=query)
                | Q(user__profile__display_name__icontains=query)
            )
        context.update(tenant=tenant, students=students, query=query)
        return context


class StudentDetailView(OrgMixin, TemplateView):
    template_name = "institute/student_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        member = get_object_or_404(
            student_members(tenant), user_id=self.kwargs["user_id"]
        )
        attempts = member.user.attempts.select_related(
            "exam", "pack", "score_breakdown"
        ).order_by("-started_at")[:50]
        context.update(tenant=tenant, member=member, attempts=attempts)
        return context


class AccessView(OrgMixin, TemplateView):
    template_name = "institute/access.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        context.update(
            tenant=tenant,
            org_members=Membership.objects.filter(
                tenant=tenant, is_active=True, role=Membership.Role.ORG
            ).select_related("user__profile"),
            invites=AccessInvite.objects.filter(tenant=tenant, is_active=True).order_by(
                "accepted_at", "email"
            ),
            seats_used=Membership.objects.filter(
                tenant=tenant, is_active=True, role=Membership.Role.STUDENT
            ).count(),
        )
        return context
