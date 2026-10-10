from django.views.generic import TemplateView

from accounts.permissions import StudentRequiredMixin
from accounts.services import get_profile
from catalog.models import Exam
from catalog.views import exam_packs, labelled_plan, practice_sections


class DashboardView(StudentRequiredMixin, TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_profile(self.request.user)
        exam = profile.primary_exam
        if exam is None or not exam.is_active:
            exam = Exam.objects.filter(code="IELTS_ACADEMIC", is_active=True).first()
        context.update(profile=profile, exam=exam)
        if exam:
            packs = exam_packs(exam, self.request)
            for pack in packs:
                pack.plan = labelled_plan(pack)
            context.update(packs=packs, sections=practice_sections(exam, self.request))
        return context
