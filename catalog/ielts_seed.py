"""Seed realistic (original) IELTS content, real-exam timings and mocks."""

from .ielts_content.listening import LISTENING_MOCK_1, LISTENING_PRACTICE
from .ielts_content.reading import READING_ACADEMIC, READING_GENERAL, READING_PRACTICE
from .ielts_content.writing_speaking import (
    SPEAKING_MOCK_1,
    SPEAKING_PRACTICE,
    WRITING_ACADEMIC,
    WRITING_GENERAL,
    WRITING_PRACTICE,
)
from .models import (
    Exam,
    MockPack,
    MockPackItem,
    Question,
    QuestionType,
    Section,
    SectionTiming,
)

S, W, R, L = Section.SPEAKING, Section.WRITING, Section.READING, Section.LISTENING
E = QuestionType.Engine

LISTENING_SET, READING_SET = 600, 1200
CATEGORIES = [
    ("L_MCQ", "Multiple choice", L, E.MCQ_SINGLE, LISTENING_SET),
    ("L_MATCH", "Matching", L, E.MATCHING, LISTENING_SET),
    ("L_MAP", "Plan / map / diagram labelling", L, E.MAP_LABEL, LISTENING_SET),
    (
        "L_FORM",
        "Form / note / table / flow-chart completion",
        L,
        E.COMPLETION,
        LISTENING_SET,
    ),
    ("L_SENT", "Sentence completion", L, E.FIB_TEXT, LISTENING_SET),
    ("L_SHORT", "Short-answer questions", L, E.FIB_TEXT, LISTENING_SET),
    ("R_MCQ", "Multiple choice", R, E.MCQ_SINGLE, READING_SET),
    ("R_TFNG", "True / False / Not Given", R, E.TFNG, READING_SET),
    ("R_YNNG", "Yes / No / Not Given (writer's views)", R, E.TFNG, READING_SET),
    ("R_MATCH_INFO", "Matching information", R, E.MATCHING, READING_SET),
    ("R_HEAD", "Matching headings", R, E.MATCHING, READING_SET),
    ("R_FEAT", "Matching features", R, E.MATCHING, READING_SET),
    ("R_END", "Matching sentence endings", R, E.MATCHING, READING_SET),
    ("R_SENT", "Sentence completion", R, E.FIB_TEXT, READING_SET),
    (
        "R_SUMM",
        "Summary / note / table / flow-chart completion",
        R,
        E.COMPLETION,
        READING_SET,
    ),
    ("R_DIAG", "Diagram label completion", R, E.MAP_LABEL, READING_SET),
    ("R_SHORT", "Short-answer questions", R, E.FIB_TEXT, READING_SET),
    ("TASK1", "Writing Task 1", W, E.WRITING_TEXT, 1200),
    ("TASK2", "Writing Task 2: Essay", W, E.WRITING_TEXT, 2400),
    ("SP1", "Speaking Part 1: Introduction & interview", S, E.SPEAKING_AUDIO, 300),
    ("SP2", "Speaking Part 2: Long turn (cue card)", S, E.SPEAKING_AUDIO, 240),
    ("SP3", "Speaking Part 3: Discussion", S, E.SPEAKING_AUDIO, 300),
]
TASK1_NAMES = {
    "IELTS_ACADEMIC": "Writing Task 1: Report (graph / table / diagram)",
    "IELTS_GENERAL": "Writing Task 1: Letter",
}
TIMINGS = [
    (L, 1800, 120, "~30 min, 4 parts × 10 questions. Paper test: +10 min transfer."),
    (R, 3600, 0, "60 min incl. transfer, 3 passages, 40 questions."),
    (W, 3600, 0, "Task 1 ~20 min (150+ words), Task 2 ~40 min (250+ words)."),
    (S, 840, 0, "11–14 min: Part 1 4–5, Part 2 3–4 (1 min prep), Part 3 4–5."),
]
MOCKS = {
    "IELTS_ACADEMIC": (
        "IELTS Academic Mock Test 1",
        LISTENING_MOCK_1,
        READING_ACADEMIC,
        WRITING_ACADEMIC,
    ),
    "IELTS_GENERAL": (
        "IELTS General Training Mock Test 1",
        LISTENING_MOCK_1,
        READING_GENERAL,
        WRITING_GENERAL,
    ),
}
PRACTICE = LISTENING_PRACTICE + READING_PRACTICE + WRITING_PRACTICE + SPEAKING_PRACTICE
SET_META = ("code", "part", "title", "answers", "transcript")


def _remove_placeholders(exam):
    exam.mock_packs.filter(slug__startswith="demo-mock-", tenant=None).delete()
    Question.objects.filter(exam=exam, title__startswith="Demo ", tenant=None).delete()
    codes = {c for c, *_ in CATEGORIES}
    exam.question_types.exclude(code__in=codes).filter(questions__isnull=True).delete()


def _question(exam, qtypes, data, difficulty):
    stem = {k: v for k, v in data.items() if k not in SET_META and v is not None}
    question, _ = Question.objects.update_or_create(
        exam=exam,
        question_type=qtypes[data["code"]],
        tenant=None,
        title=data["title"],
        defaults={
            "difficulty": difficulty,
            "is_prediction": False,
            "stem": stem,
            "answer_key": {"answers": data["answers"]} if data.get("answers") else {},
            "scorer_meta": {"transcript": data["transcript"]}
            if data.get("transcript")
            else {},
        },
    )
    return question


def seed_ielts(counts):
    for exam in Exam.objects.filter(kind=Exam.Kind.IELTS):
        _remove_placeholders(exam)
        for order, (section, seconds, extra, notes) in enumerate(TIMINGS):
            SectionTiming.objects.get_or_create(
                exam=exam,
                section=section,
                defaults={
                    "order": order,
                    "duration_sec": seconds,
                    "extra_sec": extra,
                    "notes": notes,
                },
            )
        qtypes = {}
        for code, name, section, engine, seconds in CATEGORIES:
            qtype, created = QuestionType.objects.update_or_create(
                exam=exam,
                code=code,
                defaults={
                    "name": TASK1_NAMES.get(exam.code, name)
                    if code == "TASK1"
                    else name,
                    "section": section,
                    "engine": engine,
                },
            )
            if created or qtype.default_time_sec is None:
                qtype.default_time_sec = seconds
                qtype.save(update_fields=["default_time_sec"])
            qtypes[code] = qtype
            counts["question_types"] += 1
        for data in PRACTICE:
            _question(exam, qtypes, data, difficulty=2)
            counts["questions"] += 1
        if exam.code not in MOCKS:
            continue
        title, listening, reading, writing = MOCKS[exam.code]
        sets = [(L, s) for s in listening] + [(R, s) for s in reading]
        sets += [(W, s) for s in writing] + [(S, s) for s in SPEAKING_MOCK_1]
        pack, _ = MockPack.objects.update_or_create(
            exam=exam,
            slug="mock-test-1",
            tenant=None,
            defaults={
                "title": title,
                "is_free": True,
                "duration_sec": sum(t[1] + t[2] for t in TIMINGS),
                "structure": [
                    {"section": t[0], "time_sec": t[1], "extra_sec": t[2]}
                    for t in TIMINGS
                ],
                "navigation_policy": {"allow_back_within_section": True},
            },
        )
        counts["mock_packs"] += 1
        pack.items.exclude(order__lte=len(sets)).delete()
        for order, (section, data) in enumerate(sets, start=1):
            MockPackItem.objects.update_or_create(
                pack=pack,
                order=order,
                defaults={
                    "question": _question(exam, qtypes, data, difficulty=3),
                    "section_code": section,
                    "part": data.get("part"),
                    "time_override_sec": None,
                },
            )
            counts["questions"] += 1
