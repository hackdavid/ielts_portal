"""Idempotent demo catalogue: placeholder content only, no real exam material."""

from django.db import transaction

from .ielts_seed import seed_ielts
from .models import (
    Exam,
    MockPack,
    MockPackItem,
    Question,
    QuestionType,
    Section,
    SectionTiming,
    Tag,
)

S, W, R, L = Section.SPEAKING, Section.WRITING, Section.READING, Section.LISTENING
E = QuestionType.Engine

SECTION_ORDER = {Exam.Kind.PTE: [S, W, R, L], Exam.Kind.IELTS: [L, R, W, S]}
PTE_TIMINGS = [(S, 1800), (W, 1620), (R, 1800), (L, 2580)]

PTE_TYPES = [
    ("RA", "Read Aloud", S, E.SPEAKING_AUDIO, 40),
    ("RS", "Repeat Sentence", S, E.SPEAKING_AUDIO, 15),
    ("DI", "Describe Image", S, E.SPEAKING_AUDIO, 40),
    ("RL", "Re-tell Lecture", S, E.SPEAKING_AUDIO, 40),
    ("ASQ", "Answer Short Question", S, E.SPEAKING_AUDIO, 10),
    ("SWT", "Summarize Written Text", W, E.WRITING_TEXT, 600),
    ("WE", "Write Essay", W, E.WRITING_TEXT, 1200),
    ("RW_FIB", "Reading & Writing: Fill in the Blanks", R, E.FIB_DROPDOWN, 120),
    ("MCM_R", "Multiple Choice, Multiple Answers (Reading)", R, E.MCQ_MULTI, 120),
    ("RO", "Re-order Paragraphs", R, E.REORDER, 150),
    ("R_FIB", "Reading: Fill in the Blanks", R, E.FIB_DRAG, 120),
    ("MCS_R", "Multiple Choice, Single Answer (Reading)", R, E.MCQ_SINGLE, 90),
    ("SST", "Summarize Spoken Text", L, E.WRITING_TEXT, 600),
    ("MCM_L", "Multiple Choice, Multiple Answers (Listening)", L, E.MCQ_MULTI, 90),
    ("FIB_L", "Listening: Fill in the Blanks", L, E.FIB_TEXT, 60),
    ("HCS", "Highlight Correct Summary", L, E.MCQ_SINGLE, 90),
    ("MCS_L", "Multiple Choice, Single Answer (Listening)", L, E.MCQ_SINGLE, 60),
    ("SMW", "Select Missing Word", L, E.MCQ_SINGLE, 60),
    ("HIW", "Highlight Incorrect Words", L, E.HIW, 60),
    ("WFD", "Write from Dictation", L, E.DICTATION, 60),
]
PTE_CORE_SWAPS = {
    "RL": ("RTS", "Respond to a Situation", S, E.SPEAKING_AUDIO, 40),
    "WE": ("WEM", "Write Email", W, E.WRITING_TEXT, 540),
}
TOPICS = [
    ("education", "Education"),
    ("environment", "Environment"),
    ("technology", "Technology"),
]
QUESTIONS_PER_TYPE = 3


def types_for(exam):
    if exam.code == "PTE_CORE":
        return [PTE_CORE_SWAPS.get(row[0], row) for row in PTE_TYPES]
    return PTE_TYPES


def _text(topic, n):
    return (
        f"Placeholder {topic} passage {n}. This demo text stands in for real "
        "content and is not taken from any exam paper."
    )


def _options(k=4):
    return [
        {"id": chr(97 + i), "text": f"Placeholder option {chr(65 + i)}"}
        for i in range(k)
    ]


def build_content(engine, n, topic):
    """Return (stem, answer_key, scorer_meta) for a demo question."""
    text = _text(topic, n)
    if engine == E.MCQ_SINGLE:
        return (
            {
                "passage": text,
                "prompt": "Choose the best answer.",
                "options": _options(),
            },
            {"correct": "b"},
            {},
        )
    if engine == E.MCQ_MULTI:
        stem = {
            "passage": text,
            "prompt": "Choose all correct answers.",
            "options": _options(5),
        }
        return stem, {"correct": ["a", "c"]}, {"partial_credit": "plus_minus"}
    if engine in (E.FIB_DROPDOWN, E.FIB_DRAG):
        blanks = [
            {"id": str(i), "options": ["alpha", "beta", "gamma", "delta"]}
            for i in (1, 2)
        ]
        stem = {"text": f"{text} The {{1}} affects the {{2}}.", "blanks": blanks}
        if engine == E.FIB_DRAG:
            stem = {
                "text": stem["text"],
                "bank": ["alpha", "beta", "gamma", "delta", "omega"],
            }
        return stem, {"blanks": {"1": "beta", "2": "delta"}}, {}
    if engine in (E.FIB_TEXT, E.COMPLETION):
        stem = {"text": f"{text} Notes: {{1}} and {{2}}.", "word_limit": 2}
        return stem, {"blanks": {"1": ["demo"], "2": ["sample", "samples"]}}, {}
    if engine == E.REORDER:
        paras = [
            {"id": f"p{i}", "text": f"Placeholder paragraph {i} about {topic}."}
            for i in (3, 1, 4, 2)
        ]
        return {"paragraphs": paras}, {"order": ["p1", "p2", "p3", "p4"]}, {}
    if engine == E.HIW:
        shown = (
            f"placeholder {topic} transcript with several demo words shown on screen"
        )
        return {"transcript": shown}, {"incorrect_indices": [2, 5]}, {}
    if engine in (E.MATCHING, E.MAP_LABEL):
        stem = {
            "prompt": "Match each item to an option.",
            "items": [
                {"id": str(i), "text": f"Placeholder item {i}"} for i in (1, 2, 3)
            ],
            "options": _options(5),
        }
        return stem, {"pairs": {"1": "c", "2": "a", "3": "e"}}, {}
    if engine == E.TFNG:
        stem = {
            "passage": text,
            "statements": [
                {"id": str(i), "text": f"Placeholder statement {i}."} for i in (1, 2, 3)
            ],
            "choices": ["TRUE", "FALSE", "NOT GIVEN"],
        }
        return stem, {"answers": {"1": "TRUE", "2": "NOT GIVEN", "3": "FALSE"}}, {}
    if engine == E.DICTATION:
        return (
            {"prompt": "Type the sentence you hear."},
            {"sentence": f"placeholder sentence about {topic} number {n}"},
            {},
        )
    if engine == E.WRITING_TEXT:
        stem = {
            "prompt": f"Write about this {topic} topic. {text}",
            "min_words": 50,
            "max_words": 300,
        }
        return stem, {}, {"rubric": "demo"}
    stem = {
        "prompt": f"Speak about this {topic} topic. {text}",
        "prep_sec": 30,
        "record_sec": 40,
    }
    return stem, {}, {"reference_text": text}


@transaction.atomic
def seed():
    tags = {}
    for slug, label in TOPICS:
        tags[slug], _ = Tag.objects.update_or_create(
            slug=slug, defaults={"label": label, "kind": Tag.Kind.TOPIC}
        )
    prediction_tag, _ = Tag.objects.update_or_create(
        slug="prediction", defaults={"label": "Prediction", "kind": Tag.Kind.PREDICTION}
    )
    counts = {"question_types": 0, "questions": 0, "mock_packs": 0}
    for exam in Exam.objects.filter(kind=Exam.Kind.PTE):
        by_type = {}
        for code, name, section, engine, seconds in types_for(exam):
            qtype, _ = QuestionType.objects.update_or_create(
                exam=exam,
                code=code,
                defaults={
                    "name": name,
                    "section": section,
                    "engine": engine,
                    "default_time_sec": seconds,
                },
            )
            counts["question_types"] += 1
            by_type[qtype] = []
            for n in range(1, QUESTIONS_PER_TYPE + 1):
                topic_slug = TOPICS[(n - 1) % len(TOPICS)][0]
                stem, key, meta = build_content(engine, n, topic_slug)
                question, _ = Question.objects.update_or_create(
                    exam=exam,
                    question_type=qtype,
                    tenant=None,
                    title=f"Demo {code} #{n}",
                    defaults={
                        "difficulty": n + 1,
                        "is_prediction": n == 1,
                        "stem": stem,
                        "answer_key": key,
                        "scorer_meta": meta,
                    },
                )
                question.tags.set(
                    [tags[topic_slug], prediction_tag] if n == 1 else [tags[topic_slug]]
                )
                by_type[qtype].append(question)
                counts["questions"] += 1
        for number, is_free in ((1, True), (2, False)):
            _seed_pack(exam, by_type, number, is_free)
            counts["mock_packs"] += 1
        for order, (section, seconds) in enumerate(PTE_TIMINGS):
            SectionTiming.objects.get_or_create(
                exam=exam,
                section=section,
                defaults={
                    "order": order,
                    "duration_sec": seconds,
                    "notes": "Placeholder; verify.",
                },
            )
    seed_ielts(counts)
    return counts


def _seed_pack(exam, by_type, number, is_free):
    order = SECTION_ORDER[exam.kind]
    qtypes = sorted(by_type, key=lambda qt: (order.index(qt.section), qt.code))
    structure, total = [], 0
    for section in order:
        section_types = [qt for qt in qtypes if qt.section == section]
        seconds = sum(qt.default_time_sec or 0 for qt in section_types)
        structure.append(
            {"section": section, "items": len(section_types), "time_sec": seconds}
        )
        total += seconds
    pack, _ = MockPack.objects.update_or_create(
        exam=exam,
        slug=f"demo-mock-{number}",
        defaults={
            "title": f"{exam.name} demo mock {number}",
            "is_free": is_free,
            "duration_sec": total,
            "structure": structure,
            "navigation_policy": {"allow_back": exam.kind == Exam.Kind.IELTS},
            "tenant": None,
        },
    )
    pack.items.exclude(order__lte=len(qtypes)).delete()
    for index, qtype in enumerate(qtypes, start=1):
        MockPackItem.objects.update_or_create(
            pack=pack,
            order=index,
            defaults={
                "question": by_type[qtype][number - 1],
                "section_code": qtype.section,
                "time_override_sec": None,
            },
        )
    return pack
