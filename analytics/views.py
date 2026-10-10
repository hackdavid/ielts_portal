from django.views.generic import ListView, TemplateView

from accounts.permissions import StudentRequiredMixin
from accounts.services import get_profile
from attempts.models import Attempt
from catalog.models import Exam
from catalog.views import exam_packs, labelled_plan, practice_sections

from .insights import next_step, skill_profile


class DashboardView(StudentRequiredMixin, TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        exam = profile.primary_exam
        if exam is None or not exam.is_active:
            exam = Exam.objects.filter(code="IELTS_ACADEMIC", is_active=True).first()
        attempts = self.request.user.attempts.select_related(
            "exam", "pack", "score_breakdown"
        )
        in_progress = list(
            attempts.filter(status=Attempt.Status.IN_PROGRESS).order_by("-started_at")[
                :5
            ]
        )
        context.update(
            profile=profile,
            exam=exam,
            attempt_count=attempts.count(),
            in_progress=in_progress,
            recent=attempts.exclude(status=Attempt.Status.IN_PROGRESS).order_by(
                "-submitted_at"
            )[:5],
        )
        if exam:
            packs = exam_packs(exam, self.request)
            for pack in packs:
                pack.plan = labelled_plan(pack)
            skills = skill_profile(self.request.user, exam)
            context.update(
                packs=packs,
                sections=practice_sections(exam, self.request),
                skills=skills,
                next_step=next_step(skills, exam, in_progress, packs),
            )
        return context


class ResultsView(StudentRequiredMixin, ListView):
    template_name = "analytics/results.html"
    context_object_name = "attempts"
    paginate_by = 20

    def get_queryset(self):
        return self.request.user.attempts.select_related(
            "exam", "pack", "score_breakdown"
        ).order_by("-started_at")
