from django.views.generic import TemplateView

EXAM_PLACEHOLDERS = [
    {
        "badge": "PTE",
        "name": "PTE Academic",
        "blurb": (
            "Computer-based, AI-scored on a 10–90 scale. Speaking & writing, reading, "
            "listening."
        ),
        "meta": "~2 hours · 20 task types",
        "accent": "from-aurora-1 to-aurora-2",
    },
    {
        "badge": "PTE",
        "name": "PTE Core",
        "blurb": "General-English PTE for work and migration, same adaptive drills.",
        "meta": "~2 hours · 19 task types",
        "accent": "from-aurora-2 to-fuchsia-500",
    },
    {
        "badge": "IELTS",
        "name": "IELTS Academic",
        "blurb": (
            "Real-format Listening, Reading, Writing and Speaking with official "
            "timings."
        ),
        "meta": "2 h 45 min · bands 0–9",
        "accent": "from-sky-500 to-aurora-3",
    },
    {
        "badge": "IELTS",
        "name": "IELTS General",
        "blurb": "General Training reading and letter writing for work and migration.",
        "meta": "2 h 45 min · bands 0–9",
        "accent": "from-emerald-500 to-aurora-3",
    },
]

HOW_STEPS = [
    {
        "icon": "target",
        "title": "Find your level",
        "body": (
            "Take a short diagnostic or a full mock. Every answer is scored, so we "
            "see exactly where you stand in each skill."
        ),
    },
    {
        "icon": "route",
        "title": "Get your own path",
        "body": (
            "Your next question is chosen from your weakest skill and question type, "
            "at a difficulty just above your current level."
        ),
    },
    {
        "icon": "trend",
        "title": "Close the gap",
        "body": (
            "Instant feedback, answer review and band tracking show what improved, "
            "then the path adjusts again."
        ),
    },
]

FEATURES = [
    {
        "icon": "clock",
        "title": "Real exam format and timing",
        "body": (
            "Official section structure and default timings, from 30-minute Listening "
            "to the Speaking cue card."
        ),
    },
    {
        "icon": "bolt",
        "title": "Instant practice scores",
        "body": (
            "Bands and 10–90 scores with criteria breakdowns the moment you submit."
        ),
    },
    {
        "icon": "eye",
        "title": "Answer review",
        "body": (
            "Your answer next to the correct one, plus Listening scripts and your own "
            "recordings."
        ),
    },
    {
        "icon": "mic",
        "title": "Speaking and listening, done properly",
        "body": "Mic check, timed recording and play-once audio, just like test day.",
    },
]

FAQS = [
    {
        "q": "How is this different from other practice apps?",
        "a": (
            "Most apps give every student the same fixed question bank in the same "
            "order. Here, the questions you see next depend on your own scores, by "
            "skill, question type and difficulty, so two students rarely get the same "
            "path."
        ),
    },
    {
        "q": "How does it decide what I should practise next?",
        "a": (
            "It looks at your scored attempts, finds the section and question type "
            "pulling your score down, and points you there first. We are extending "
            "this with a deeper AI model that also adjusts difficulty question by "
            "question."
        ),
    },
    {
        "q": "Are the scores official?",
        "a": (
            "No. Scores are practice approximations designed to track progress. They "
            "are not issued or endorsed by Pearson, IDP, the British Council or "
            "Cambridge."
        ),
    },
    {
        "q": "Is the content copied from real exams?",
        "a": (
            "No. All passages, recordings and prompts are original and written to "
            "match the real format, question types and timing."
        ),
    },
    {
        "q": "Can my institute use it with our students?",
        "a": (
            "Yes. Institutes get their own space: you add student emails, they sign "
            "in with Google, and you follow their progress from the org dashboard."
        ),
    },
]


class HomeView(TemplateView):
    template_name = "pages/home.html"
    extra_context = {
        "exams": EXAM_PLACEHOLDERS,
        "steps": HOW_STEPS,
        "features": FEATURES,
        "faqs": FAQS,
    }


class AboutView(TemplateView):
    template_name = "pages/about.html"


class InstitutesView(TemplateView):
    template_name = "pages/institutes.html"


class ContactView(TemplateView):
    template_name = "pages/contact.html"
