from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from accounts.permissions import RoleRequiredMixin

from .access import mark_locked, visible
from .demo import SECTION_ORDER
from .models import Exam, MockPack, Question, Section, Tag

SECTION_LABELS = dict(Section.choices)


def _chip(request, key, value, label):
    params = request.GET.copy()
    active = params.get(key) == value
    if active:
        params.pop(key)
    else:
        params[key] = value
    query = params.urlencode()
    return {"label": label, "url": f"?{query}" if query else "?", "active": active}


def practice_sections(exam, request):
    """Question categories grouped by section (exam order) with visible counts."""
    questions = visible(Question.objects.filter(exam=exam), request)
    counts = dict(
        questions.values("question_type")
        .annotate(n=Count("id"))
        .values_list("question_type", "n")
    )
    sections = []
    for section in SECTION_ORDER.get(exam.kind, [c for c, _ in Section.choices]):
        qtypes = list(exam.question_types.filter(section=section).order_by("pk"))
        for qt in qtypes:
            qt.question_count = counts.get(qt.pk, 0)
        if qtypes:
            sections.append(
                {"code": section, "label": SECTION_LABELS[section], "qtypes": qtypes}
            )
    return sections


def labelled_plan(pack):
    item_counts = dict(
        pack.items.values("section_code")
        .annotate(n=Count("id"))
        .values_list("section_code", "n")
    )
    plan = pack.section_plan()
    for row in plan:
        row["label"] = SECTION_LABELS.get(row["section"], row["section"])
        row["sets"] = item_counts.get(row["section"], 0)
    return plan


def exam_packs(exam, request):
    packs = visible(exam.mock_packs.annotate(item_count=Count("items")), request)
    return mark_locked(request, packs.order_by("-is_free", "title"))


class ExamMixin(RoleRequiredMixin):
    def get_exam(self):
        return get_object_or_404(Exam, slug=self.kwargs["slug"], is_active=True)


class ExamListView(RoleRequiredMixin, TemplateView):
    template_name = "catalog/exam_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exams = list(
            Exam.objects.filter(is_active=True).annotate(
                type_count=Count("question_types")
            )
        )
        for exam in exams:
            exam.mock_count = visible(exam.mock_packs.all(), self.request).count()
        context["exams"] = exams
        return context


class ExamDetailView(ExamMixin, TemplateView):
    template_name = "catalog/exam_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam = self.get_exam()
        context.update(
            exam=exam,
            sections=practice_sections(exam, self.request),
            packs=exam_packs(exam, self.request),
            tab=self.request.GET.get("tab")
            if self.request.GET.get("tab") in ("mocks", "types", "sections")
            else "mocks",
        )
        return context


class QuestionTypeListView(ExamMixin, TemplateView):
    template_name = "catalog/qtype_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam = self.get_exam()
        qtype = get_object_or_404(exam.question_types, code=self.kwargs["code"])
        params = self.request.GET
        questions = visible(Question.objects.filter(question_type=qtype), self.request)
        if params.get("prediction") == "1":
            questions = questions.filter(is_prediction=True)
        if params.get("difficulty") in {str(i) for i in range(1, 6)}:
            questions = questions.filter(difficulty=int(params["difficulty"]))
        topics = Tag.objects.filter(
            kind=Tag.Kind.TOPIC, questions__question_type=qtype
        ).distinct()
        if params.get("topic"):
            questions = questions.filter(tags__slug=params["topic"])
        context.update(
            exam=exam,
            qtype=qtype,
            questions=questions.only("id", "title", "difficulty", "is_prediction")
            .prefetch_related("tags")
            .order_by("title")
            .distinct(),
            prediction_chip=_chip(self.request, "prediction", "1", "Prediction"),
            difficulty_chips=[
                _chip(self.request, "difficulty", str(i), f"Level {i}")
                for i in range(1, 6)
            ],
            topic_chips=[_chip(self.request, "topic", t.slug, t.label) for t in topics],
            filtered=any(params.get(k) for k in ("prediction", "difficulty", "topic")),
        )
        return context


class MockListView(ExamMixin, TemplateView):
    template_name = "catalog/mock_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam = self.get_exam()
        packs = visible(
            exam.mock_packs.annotate(item_count=Count("items")), self.request
        )
        if self.request.GET.get("free") == "1":
            packs = packs.filter(is_free=True)
        context.update(
            exam=exam,
            packs=mark_locked(self.request, packs.order_by("-is_free", "title")),
            free_chip=_chip(self.request, "free", "1", "Free only"),
        )
        return context


def _get_pack(request, pk):
    pack = get_object_or_404(
        visible(MockPack.objects.select_related("exam"), request), pk=pk
    )
    return mark_locked(request, [pack])[0]


class MockDetailView(RoleRequiredMixin, TemplateView):
    template_name = "catalog/mock_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pack = _get_pack(self.request, self.kwargs["pk"])
        context.update(
            pack=pack,
            exam=pack.exam,
            sections=labelled_plan(pack),
            item_count=pack.items.count(),
        )
        return context


@method_decorator(require_POST, name="dispatch")
class StartMockView(RoleRequiredMixin, TemplateView):
    template_name = "catalog/start_pending.html"

    def post(self, request, *args, **kwargs):
        pack = _get_pack(request, kwargs["pk"])
        if pack.locked:
            return redirect("plans:locked")
        return render(request, self.template_name, {"pack": pack}, status=501)
