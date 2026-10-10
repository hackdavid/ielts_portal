from django.conf import settings


def site(request):
    return {
        "PRACTICE_SCORE_DISCLAIMER": settings.PRACTICE_SCORE_DISCLAIMER,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "auth_context": getattr(request, "auth_context", None),
    }


STUDENT_NAV = [
    ("Dashboard", "home", {"analytics:dashboard"}),
    (
        "Practice",
        "grid",
        {"catalog:exam_list", "catalog:exam_detail", "catalog:qtype_list"},
    ),
    (
        "Mock tests",
        "layers",
        {"catalog:mock_list", "catalog:mock_detail", "plans:locked"},
    ),
    ("Results", "chart", {"analytics:results", "attempts:done", "attempts:review"}),
]
ORG_NAV = [
    ("Overview", "home", {"institute:console"}),
    ("Students", "users", {"institute:students", "institute:student_detail"}),
    ("Access & invites", "mail", {"institute:access"}),
]


def _student_urls(user):
    from django.urls import reverse

    from accounts.services import get_profile
    from catalog.models import Exam

    exam = get_profile(user).primary_exam
    if exam is None or not exam.is_active:
        exam = Exam.objects.filter(code="IELTS_ACADEMIC", is_active=True).first()
    exams = reverse("catalog:exam_list")
    return [
        reverse("analytics:dashboard"),
        reverse("catalog:exam_detail", args=[exam.slug]) + "?tab=types"
        if exam
        else exams,
        reverse("catalog:mock_list", args=[exam.slug]) if exam else exams,
        reverse("analytics:results"),
    ]


def app_nav(request):
    """Sidebar / bottom-tab items for the student and org app shells."""
    from django.urls import reverse

    from accounts.models import Role

    context = getattr(request, "auth_context", None)
    if not context or not request.user.is_authenticated:
        return {}
    match = request.resolver_match
    view = match.view_name if match else ""
    if context["role"] == Role.STUDENT:
        rows, urls = STUDENT_NAV, _student_urls(request.user)
    elif context["role"] == Role.ORG:
        rows = ORG_NAV
        urls = [
            reverse(n)
            for n in ("institute:console", "institute:students", "institute:access")
        ]
    else:
        return {}
    return {
        "app_nav": [
            {"label": label, "icon": icon, "url": url, "active": view in names}
            for (label, icon, names), url in zip(rows, urls)
        ]
    }
