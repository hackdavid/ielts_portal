"""Agent instructions and typed outputs for analyst, planner and reviewer.

The writer's output type is the engine contract (content.contracts).
"""

from pydantic import BaseModel, Field

WRITING_WORDS = {
    "TASK1": (150, None),
    "TASK2": (250, None),
    "SWT": (5, 75),
    "SST": (50, 70),
    "WE": (200, 300),
    "WEM": (50, 120),
}


class Finding(BaseModel):
    question_type_code: str | None = Field(
        description="Code from the provided list, or null if none fits."
    )
    detected_label: str = Field(description="What the source calls this task.")
    instructions_wording: str = ""
    item_count: int | None = None
    answer_format: str = Field("", description="e.g. 'ONE WORD AND/OR A NUMBER'.")
    word_limit: int | None = None
    stimulus_words: int | None = Field(None, description="Approx. passage length.")
    distractor_style: str = ""
    difficulty_signals: str = ""
    page_refs: list[int] = Field(default_factory=list)


class Analysis(BaseModel):
    findings: list[Finding]


class PlannedBrief(BaseModel):
    topic: str
    subtopic: str
    difficulty: int = Field(ge=1, le=5)
    angle: str = Field(description="One line: the specific scenario or argument.")


class Plan(BaseModel):
    briefs: list[PlannedBrief]


class ReviewAnswer(BaseModel):
    key: str
    answer: str = Field(description="Your answer; for lists join with ', '.")


class Review(BaseModel):
    answers: list[ReviewAnswer] = Field(default_factory=list)
    quality: int = Field(3, ge=1, le=5, description="5 = exam-ready.")
    ambiguous: list[str] = Field(
        default_factory=list, description="Keys with more than one defensible answer."
    )
    issues: list[str] = Field(default_factory=list)


ANALYST = """You analyse IELTS / PTE practice material. For every distinct task
format in the pages, map it to ONE code from `question_types` (or null). Describe
the pattern (instructions wording, item count, answer format, word limit,
approximate passage/script length, how distractors work, difficulty signals) and
the page numbers. Describe patterns only; never copy passages or questions."""

PLANNER = """You plan new, ORIGINAL exam questions. Propose exactly `count` briefs
for the given question type. Spread topics widely, follow `difficulty_mix`, and
avoid every topic/subtopic listed in `existing_topics` (those are already in the
bank). Prefer `topic_hints` when given. Each brief needs a concrete angle."""

WRITER = """You write one ORIGINAL {exam} question of type {code} ({name}).
Rules:
- Follow the real exam format and the learned `patterns` (format only).
- Never copy sentences from any source; invent all content, names and numbers.
- Stimulus: {stimulus_rule}
- Every answer must be unambiguous and supported by the text/script; give an
  explanation and, where possible, an exact evidence quote.
- Item numbers start at {first_item}. Use realistic British English.
- Policy (lengths, counts): {policy}
{extra}"""

REVIEWER = """You are a strict exam reviewer. Answer every question yourself using
ONLY the student material (the script stands in for the audio). Then rate quality
1–5 and list ambiguous keys and problems (unclear wording, two possible answers,
answer not in text, unnatural language, format errors)."""

STIMULUS_RULES = {
    "passage": "write the reading passage in stimulus.passage.",
    "audio": "write the recording as stimulus.script turns (speaker + text); "
    "it becomes TTS audio and is never shown to the student.",
    "map": "write stimulus.script, an image_prompt for a plan WITHOUT any text "
    "or letters, and map_labels (letter + x/y 0–1) for each place.",
    "chart": "put exact data in stimulus.chart (it is drawn by code).",
    "image": "write an image_prompt describing the picture.",
    None: "no shared stimulus; leave stimulus empty.",
}

EXTRA = {
    "R_TFNG": "Options are exactly TRUE, FALSE, NOT GIVEN.",
    "R_YNNG": "Options are exactly YES, NO, NOT GIVEN (writer's views).",
    "R_HEAD": "Label paragraphs A, B, C… in the passage; options are roman numerals "
    "i, ii, iii… listed in `context` with more headings than paragraphs.",
    "L_MAP": "Options are letters A–G; answers are letters.",
    "SMW": "The script must stop just before the missing final words; the "
    "correct option completes it.",
    "HIW": "`shown` = `spoken` with 2–4 single words replaced by plausible "
    "alternatives; same number of words.",
    "FIB_L": "`text` is the transcript with {1}, {2}… replacing single words; "
    "the script says the full sentence.",
    "RW_FIB": "Use {1}, {2}… in `text`; each blank has 4 options.",
    "R_FIB": "Use {1}, {2}… in `text`; `bank` has all answers plus 2–3 distractors.",
    "RO": "List paragraphs in the correct order; we shuffle them.",
    "ASQ": "One short question; expected_answers = acceptable one/two-word answers.",
}
