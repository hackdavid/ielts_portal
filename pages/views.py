from django.views.generic import TemplateView

EXAM_PLACEHOLDERS = [
    {
        "badge": "PTE",
        "name": "PTE Academic",
        "blurb": "Speaking, writing, reading, listening.",
    },
    {"badge": "PTE", "name": "PTE Core", "blurb": "General-purpose PTE practice."},
    {
        "badge": "IELTS",
        "name": "IELTS Academic",
        "blurb": "CD-IELTS style mocks and drills.",
    },
    {
        "badge": "IELTS",
        "name": "IELTS General",
        "blurb": "General Training reading & writing.",
    },
]


class HomeView(TemplateView):
    template_name = "pages/home.html"
    extra_context = {"exams": EXAM_PLACEHOLDERS}


class AboutView(TemplateView):
    template_name = "pages/about.html"


class ContactView(TemplateView):
    template_name = "pages/contact.html"
