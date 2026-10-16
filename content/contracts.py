"""Typed generation contracts: one Pydantic model per engine family.

A contract is (1) the writer agent's structured output, (2) the thing we validate
mechanically, and (3) the JSON Schema stored on QuestionType.content_schema.
`build()` turns a contract into the existing Question stem / answer_key /
scorer_meta shapes, so the player and scorers need no changes.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from catalog.models import Exam, QuestionType

E = QuestionType.Engine
WORD = re.compile(r"[A-Za-z0-9'’-]+")
BLANK = re.compile(r"\{(\w+)\}")
TFNG = ["TRUE", "FALSE", "NOT GIVEN"]
YNNG = ["YES", "NO", "NOT GIVEN"]


def words(text):
    return WORD.findall(text or "")


def norm(text):
    return " ".join(w.lower() for w in words(text))


# ---------------------------------------------------------------- shared parts


class Turn(BaseModel):
    speaker: str = Field(description="Speaker label, e.g. 'Receptionist'.")
    text: str


class ChartSeries(BaseModel):
    name: str
    values: list[float]


class ChartSpec(BaseModel):
    """Exact data for a code-rendered chart (values are part of the answer)."""

    chart_type: Literal["bar", "line", "pie", "table"]
    title: str
    categories: list[str] = Field(description="X-axis labels / pie slices / rows.")
    series: list[ChartSeries]
    x_label: str = ""
    y_label: str = ""
    unit: str = Field("", description="e.g. '%', 'million', '°C'.")


class MapLabel(BaseModel):
    letter: str
    x: float = Field(ge=0, le=1, description="Horizontal position 0–1.")
    y: float = Field(ge=0, le=1, description="Vertical position 0–1.")


class StimulusSpec(BaseModel):
    title: str = ""
    passage: str = Field("", description="Reading text shown to the student.")
    script: list[Turn] = Field(
        default_factory=list, description="Listening audio, one entry per turn."
    )
    chart: ChartSpec | None = None
    image_prompt: str = Field(
        "", description="Photo / scene / map description for the image model."
    )
    map_labels: list[MapLabel] = Field(default_factory=list)


class Item(BaseModel):
    n: int
    text: str
    options: list[str] = Field(default_factory=list)


class Answer(BaseModel):
    key: str = Field(description="Item number / statement id / blank id.")
    accepted: list[str] = Field(description="Accepted answers, best first.")
    explanation: str = ""
    evidence: str = Field("", description="Exact quote from passage or script.")


class Option(BaseModel):
    id: str
    text: str


class Blank(BaseModel):
    id: str
    options: list[str] = Field(default_factory=list)


class CueCard(BaseModel):
    topic: str
    points: list[str]
    explain: str = ""


class Contract(BaseModel):
    title: str = Field(description="Internal title, unique and descriptive.")
    topic: str
    subtopic: str = ""
    difficulty: int = Field(3, ge=1, le=5)
    instructions: str = ""
    stimulus: StimulusSpec = Field(default_factory=StimulusSpec)


# ---------------------------------------------------------------- per engine


class ItemsContract(Contract):
    """IELTS numbered items: completion, MCQ, matching, map, TFNG, short answer."""

    context: str = Field("", description="Form heading, list of options, etc.")
    word_limit: int | None = None
    items: list[Item]
    answers: list[Answer]


class McqContract(Contract):
    """PTE single / multiple answer MCQ, HCS, SMW."""

    prompt: str
    options: list[Option]
    correct: list[str]
    explanation: str = ""


class InlineFibContract(Contract):
    """PTE inline blanks: '{1}' placeholders in `text`."""

    text: str
    blanks: list[Blank] = Field(
        default_factory=list, description="Dropdown options per blank."
    )
    bank: list[str] = Field(default_factory=list, description="Drag-drop word bank.")
    answers: list[Answer]


class ReorderContract(Contract):
    paragraphs: list[str] = Field(description="Paragraphs in the CORRECT order.")


class HiwContract(Contract):
    spoken: str = Field(description="What the audio says.")
    shown: str = Field(description="Same text with 2–4 single words replaced.")


class DictationContract(Contract):
    sentence: str


class WritingContract(Contract):
    prompt: str
    min_words: int
    max_words: int | None = None
    model_answer: str = ""
    rubric_notes: str = ""


class SpeakingContract(Contract):
    prompt: str = ""
    read_text: str = Field("", description="Read Aloud text.")
    questions: list[str] = Field(default_factory=list)
    cue_card: CueCard | None = None
    prep_sec: int = 0
    record_sec: int = 40
    expected_answers: list[str] = Field(
        default_factory=list, description="Answer Short Question accepted answers."
    )
    model_answer: str = ""


CONTRACTS = {
    "items": ItemsContract,
    "mcq": McqContract,
    "inline": InlineFibContract,
    "reorder": ReorderContract,
    "hiw": HiwContract,
    "dictation": DictationContract,
    "writing": WritingContract,
    "speaking": SpeakingContract,
}


# ---------------------------------------------------------------- media / length policy

# stimulus: passage | audio | chart | image | map | None ; words = stimulus length
POLICIES = {
    # IELTS listening (one recording per set; script is server-only)
    "L_FORM": {"stimulus": "audio", "voices": 2, "words": (250, 700), "items": (5, 10)},
    "L_MCQ": {"stimulus": "audio", "voices": 2, "words": (250, 700), "items": (3, 10)},
    "L_MATCH": {"stimulus": "audio", "voices": 1, "words": (250, 700), "items": (4, 8)},
    "L_MAP": {"stimulus": "map", "voices": 1, "words": (250, 700), "items": (4, 8)},
    "L_SENT": {"stimulus": "audio", "voices": 1, "words": (250, 800), "items": (4, 10)},
    "L_SHORT": {"stimulus": "audio", "voices": 2, "words": (250, 700), "items": (3, 8)},
    # IELTS reading (shared passage)
    **{
        code: {"stimulus": "passage", "words": (500, 1000), "items": (4, 10)}
        for code in (
            "R_MCQ R_TFNG R_YNNG R_MATCH_INFO R_HEAD R_FEAT R_END R_SENT R_SUMM R_SHORT"
        ).split()
    },
    "R_DIAG": {
        "stimulus": "passage",
        "image": True,
        "words": (500, 1000),
        "items": (3, 8),
    },
    "TASK1": {"stimulus": "chart", "academic_only": True},
    "TASK2": {"stimulus": None},
    "SP1": {"stimulus": None, "questions": (4, 8)},
    "SP2": {"stimulus": None},
    "SP3": {"stimulus": None, "questions": (3, 6)},
    # PTE
    "RA": {"stimulus": None, "read_words": (35, 70)},
    "RS": {"stimulus": "audio", "voices": 1, "words": (6, 14)},
    "DI": {"stimulus": "chart"},
    "RL": {"stimulus": "audio", "voices": 1, "words": (120, 300)},
    "RTS": {"stimulus": "audio", "voices": 1, "words": (30, 90)},
    "ASQ": {"stimulus": "audio", "voices": 1, "words": (5, 25)},
    "SWT": {"stimulus": "passage", "words": (180, 320)},
    "WE": {"stimulus": None},
    "WEM": {"stimulus": None},
    "RW_FIB": {"stimulus": None, "text_words": (70, 160), "blanks": (3, 6)},
    "MCM_R": {"stimulus": "passage", "words": (150, 320)},
    "MCS_R": {"stimulus": "passage", "words": (100, 300)},
    "RO": {"stimulus": None, "paragraphs": (4, 5)},
    "R_FIB": {"stimulus": None, "text_words": (70, 160), "blanks": (3, 6)},
    "SST": {"stimulus": "audio", "voices": 1, "words": (120, 300)},
    "MCM_L": {"stimulus": "audio", "voices": 1, "words": (100, 280)},
    "FIB_L": {"stimulus": "audio", "voices": 1, "words": (50, 140), "blanks": (3, 6)},
    "HCS": {"stimulus": "audio", "voices": 1, "words": (100, 280)},
    "MCS_L": {"stimulus": "audio", "voices": 1, "words": (100, 280)},
    "SMW": {"stimulus": "audio", "voices": 1, "words": (50, 140)},
    "HIW": {"stimulus": "audio", "voices": 1, "words": (40, 100)},
    "WFD": {"stimulus": "audio", "voices": 1, "words": (6, 14)},
}
SPEAKING_TIMES = {
    "RA": (35, 40),
    "RS": (0, 15),
    "DI": (25, 40),
    "RL": (10, 40),
    "RTS": (20, 40),
    "ASQ": (3, 10),
    "SP1": (0, 300),
    "SP2": (60, 120),
    "SP3": (0, 300),
}


def policy_for(qtype):
    base = dict(POLICIES.get(qtype.code, {}))
    if base.get("academic_only") and qtype.exam.code != "IELTS_ACADEMIC":
        base["stimulus"] = None
    base.update(qtype.media_policy or {})
    return base


def contract_kind(qtype):
    ielts = qtype.exam.kind == Exam.Kind.IELTS
    engine = qtype.engine
    if engine == E.WRITING_TEXT:
        return "writing"
    if engine == E.SPEAKING_AUDIO:
        return "speaking"
    if engine == E.REORDER:
        return "reorder"
    if engine == E.HIW:
        return "hiw"
    if engine == E.DICTATION:
        return "dictation"
    if ielts:
        return "items"
    if engine in (E.MCQ_SINGLE, E.MCQ_MULTI):
        return "mcq"
    return "inline"


def contract_for(qtype):
    return CONTRACTS[contract_kind(qtype)]


def json_schema(qtype):
    return contract_for(qtype).model_json_schema()


# ---------------------------------------------------------------- building


@dataclass
class Built:
    stem: dict
    answer_key: dict
    scorer_meta: dict
    explanations: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)


def script_text(spec):
    return " ".join(t.text for t in spec.script)


def _shuffle(ids, seed):
    return sorted(ids, key=lambda i: hashlib.sha256(f"{seed}:{i}".encode()).digest())


def _letters(n):
    return [chr(97 + i) for i in range(n)]


def build(contract, qtype):
    """Contract → existing stem / answer_key / scorer_meta shapes."""
    s = contract.stimulus
    stem = {}
    if contract.instructions:
        stem["instructions"] = contract.instructions
    if s.passage:
        stem["passage"] = s.passage
    meta = {}
    if s.script:
        meta["transcript"] = script_text(s)
        meta["script"] = [t.model_dump() for t in s.script]
    if s.chart:
        stem["data_table"] = chart_table(s.chart)
    expl = {}

    if isinstance(contract, ItemsContract):
        if contract.context:
            stem["context"] = contract.context
        if contract.word_limit:
            stem["word_limit"] = contract.word_limit
        stem["items"] = [
            {"n": i.n, "text": i.text, **({"options": i.options} if i.options else {})}
            for i in contract.items
        ]
        options = {str(i.n): i.options for i in contract.items}
        answers = {}
        for a in contract.answers:
            answers[a.key] = a.accepted[0] if options.get(a.key) else a.accepted
            expl[a.key] = {"why": a.explanation, "evidence": a.evidence}
        return Built(stem, {"answers": answers}, meta, expl)

    if isinstance(contract, McqContract):
        ids = _letters(len(contract.options))
        by_old = {o.id: new for o, new in zip(contract.options, ids, strict=True)}
        stem["prompt"] = contract.prompt
        stem["options"] = [
            {"id": new, "text": o.text}
            for o, new in zip(contract.options, ids, strict=True)
        ]
        correct = [by_old.get(c, c) for c in contract.correct]
        multi = qtype.engine == E.MCQ_MULTI
        key = {"correct": correct if multi else (correct[0] if correct else "")}
        if multi:
            meta["partial_credit"] = "plus_minus"
        expl["answer"] = {"why": contract.explanation}
        return Built(stem, key, meta, expl)

    if isinstance(contract, InlineFibContract):
        stem["text"] = contract.text
        blanks = {}
        for a in contract.answers:
            blanks[a.key] = a.accepted if qtype.engine == E.FIB_TEXT else a.accepted[0]
            expl[a.key] = {"why": a.explanation}
        if qtype.engine == E.FIB_DROPDOWN:
            stem["blanks"] = [b.model_dump() for b in contract.blanks]
        elif qtype.engine == E.FIB_DRAG:
            stem["bank"] = sorted(contract.bank, key=str.lower)
        return Built(stem, {"blanks": blanks}, meta, expl)

    if isinstance(contract, ReorderContract):
        ids = [f"p{i}" for i in range(1, len(contract.paragraphs) + 1)]
        text = dict(zip(ids, contract.paragraphs, strict=True))
        shuffled = _shuffle(ids, contract.title)
        if shuffled == ids and len(ids) > 1:
            shuffled = ids[1:] + ids[:1]
        stem["paragraphs"] = [{"id": i, "text": text[i]} for i in shuffled]
        return Built(stem, {"order": ids}, meta, expl)

    if isinstance(contract, HiwContract):
        spoken, shown = contract.spoken.split(), contract.shown.split()
        wrong = [
            i
            for i, (a, b) in enumerate(zip(spoken, shown, strict=False))
            if norm(a) != norm(b)
        ]
        stem["transcript"] = contract.shown
        meta["transcript"] = contract.spoken
        return Built(stem, {"incorrect_indices": wrong}, meta, expl)

    if isinstance(contract, DictationContract):
        stem["prompt"] = contract.instructions or "Type the sentence you hear."
        meta["transcript"] = contract.sentence
        return Built(stem, {"sentence": contract.sentence}, meta, expl)

    if isinstance(contract, WritingContract):
        stem["prompt"] = contract.prompt
        stem["min_words"] = contract.min_words
        if contract.max_words:
            stem["max_words"] = contract.max_words
        meta.update(model_answer=contract.model_answer, rubric=contract.rubric_notes)
        return Built(stem, {}, meta, expl)

    # speaking
    if contract.prompt:
        stem["prompt"] = contract.prompt
    if contract.read_text:
        stem["passage"] = contract.read_text
    if contract.questions:
        stem["questions"] = contract.questions
    if contract.cue_card:
        stem["cue_card"] = contract.cue_card.model_dump()
    stem["prep_sec"] = contract.prep_sec
    stem["talk_sec" if qtype.code == "SP2" else "record_sec"] = contract.record_sec
    key = {"expected": contract.expected_answers} if contract.expected_answers else {}
    meta["model_answer"] = contract.model_answer
    return Built(stem, key, meta, expl)


def chart_table(chart):
    columns = [chart.x_label or "Category", *[s.name for s in chart.series]]
    unit = chart.unit or ""
    rows = [
        [cat, *[f"{_fmt(s.values[i])}{unit}" for s in chart.series]]
        for i, cat in enumerate(chart.categories)
        if all(i < len(s.values) for s in chart.series)
    ]
    return {"columns": columns, "rows": rows}


def _fmt(v):
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


# ---------------------------------------------------------------- validation


def check(contract, qtype):
    """Mechanical checks → list of {level, code, message}. Errors block publish."""
    issues = []
    pol = policy_for(qtype)
    s = contract.stimulus

    def err(code, msg, level="error"):
        issues.append({"level": level, "code": code, "message": msg})

    def in_range(n, bounds, what):
        if bounds and not (bounds[0] <= n <= bounds[1]):
            err("length", f"{what} has {n}; expected {bounds[0]}–{bounds[1]}.")

    kind = pol.get("stimulus")
    if kind == "passage":
        if not s.passage:
            err("stimulus", "A reading passage is required.")
        in_range(len(words(s.passage)), pol.get("words"), "Passage word count")
    if kind in ("audio", "map"):
        if not s.script and not isinstance(contract, HiwContract | DictationContract):
            err("stimulus", "A listening script is required.")
        if s.script:
            in_range(len(words(script_text(s))), pol.get("words"), "Script word count")
            speakers = {t.speaker for t in s.script}
            if pol.get("voices", 1) >= 2 and len(speakers) < 2:
                err("voices", "This part needs a dialogue (2+ speakers).", "warning")
    if kind == "chart":
        if not s.chart:
            err("stimulus", "Chart data is required.")
        else:
            n = len(s.chart.categories)
            for series in s.chart.series:
                if len(series.values) != n:
                    err("chart", f"Series '{series.name}' needs {n} values.")
            if s.chart.chart_type == "pie" and len(s.chart.series) != 1:
                err("chart", "A pie chart takes exactly one series.")
    if kind == "map" and not s.map_labels:
        err("stimulus", "Map labels (letters with positions) are required.")
    if pol.get("image") and not s.image_prompt:
        err("stimulus", "An image prompt is required for this diagram.", "warning")
    if kind is None and (s.script or s.passage) and qtype.code not in ("TASK1",):
        err("stimulus", "This type takes no shared stimulus.", "warning")

    if isinstance(contract, ItemsContract):
        _check_items(contract, qtype, pol, err)
    elif isinstance(contract, McqContract):
        ids = [o.id for o in contract.options]
        if len(set(ids)) != len(ids):
            err("options", "Option ids must be unique.")
        bad = [c for c in contract.correct if c not in ids]
        if bad:
            err("key", f"Correct answer(s) {bad} are not options.")
        if qtype.engine == E.MCQ_SINGLE and len(contract.correct) != 1:
            err("key", "Single-answer MCQ needs exactly one correct option.")
        if qtype.engine == E.MCQ_MULTI and not 2 <= len(contract.correct) < len(ids):
            err("key", "Multiple-answer MCQ needs 2+ correct, not all options.")
        if not 4 <= len(ids) <= 7:
            err("options", f"{len(ids)} options; expected 4–7.")
    elif isinstance(contract, InlineFibContract):
        _check_inline(contract, qtype, pol, err)
    elif isinstance(contract, ReorderContract):
        in_range(len(contract.paragraphs), pol.get("paragraphs"), "Paragraph count")
        if len({norm(p) for p in contract.paragraphs}) != len(contract.paragraphs):
            err("paragraphs", "Paragraphs must be distinct.")
    elif isinstance(contract, HiwContract):
        spoken, shown = contract.spoken.split(), contract.shown.split()
        if len(spoken) != len(shown):
            err("hiw", "Shown and spoken text must have the same number of words.")
        diffs = sum(
            1 for a, b in zip(spoken, shown, strict=False) if norm(a) != norm(b)
        )
        if not 2 <= diffs <= 5:
            err("hiw", f"{diffs} changed words; expected 2–5.")
        in_range(len(spoken), pol.get("words"), "Transcript word count")
    elif isinstance(contract, DictationContract):
        in_range(len(words(contract.sentence)), pol.get("words"), "Sentence words")
    elif isinstance(contract, WritingContract):
        if len(words(contract.prompt)) < 10:
            err("prompt", "Prompt is too short.")
        if contract.model_answer:
            n = len(words(contract.model_answer))
            if n < contract.min_words:
                err("model", f"Model answer {n} words < minimum.", "warning")
    elif isinstance(contract, SpeakingContract):
        if pol.get("read_words"):
            in_range(len(words(contract.read_text)), pol["read_words"], "Read text")
        if pol.get("questions"):
            in_range(len(contract.questions), pol["questions"], "Question count")
        if qtype.code == "SP2" and not contract.cue_card:
            err("cue_card", "Part 2 needs a cue card.")
        if qtype.code == "ASQ" and not contract.expected_answers:
            err("key", "Answer Short Question needs expected answers.")
    return issues


def _check_items(c, qtype, pol, err):
    s = c.stimulus
    keys = [str(i.n) for i in c.items]
    if len(set(keys)) != len(keys):
        err("items", "Item numbers must be unique.")
    nums = [i.n for i in c.items]
    if nums and nums != list(range(nums[0], nums[0] + len(nums))):
        err("items", "Item numbers must be consecutive.")
    if pol.get("items") and not (pol["items"][0] <= len(nums) <= pol["items"][1]):
        lo, hi = pol["items"]
        err("items", f"{len(nums)} items; expected {lo}–{hi}.")
    answers = {a.key: a for a in c.answers}
    if set(answers) != set(keys):
        err("key", f"Answers {sorted(answers)} do not match items {keys}.")
    source = norm(s.passage) if s.passage else norm(script_text(s))
    choices = TFNG if qtype.code != "R_YNNG" else YNNG
    for item in c.items:
        a = answers.get(str(item.n))
        if not a or not a.accepted:
            continue
        if item.options:
            heads = [o.split(" ")[0] for o in item.options]
            if a.accepted[0] not in item.options + heads:
                err("key", f"Q{item.n}: answer '{a.accepted[0]}' is not an option.")
        else:
            if c.word_limit:
                for value in a.accepted:
                    if len(words(value)) > c.word_limit:
                        err("word_limit", f"Q{item.n}: '{value}' over word limit.")
            if source and not any(norm(v) and norm(v) in source for v in a.accepted):
                err("answerable", f"Q{item.n}: answer not found in the text/script.")
        if qtype.engine == E.TFNG:
            if item.options and item.options != choices:
                err("options", f"Q{item.n}: options must be {choices}.")
            if a.accepted[0] != "NOT GIVEN":
                if not a.evidence:
                    err("evidence", f"Q{item.n}: evidence quote missing.", "warning")
                elif norm(a.evidence) not in source:
                    err("evidence", f"Q{item.n}: evidence is not in the passage.")


def _check_inline(c, qtype, pol, err):
    placeholders = BLANK.findall(c.text)
    answers = {a.key: a for a in c.answers}
    if set(placeholders) != set(answers):
        err("key", f"Blanks {placeholders} do not match answers {sorted(answers)}.")
    if len(placeholders) != len(set(placeholders)):
        err("blanks", "Each blank id must appear once.")
    if pol.get("blanks"):
        lo, hi = pol["blanks"]
        if not lo <= len(placeholders) <= hi:
            err("blanks", f"{len(placeholders)} blanks; expected {lo}–{hi}.")
    if pol.get("text_words"):
        lo, hi = pol["text_words"]
        n = len(words(BLANK.sub("x", c.text)))
        if not lo <= n <= hi:
            err("length", f"Text has {n} words; expected {lo}–{hi}.")
    if qtype.engine == E.FIB_DROPDOWN:
        options = {b.id: b.options for b in c.blanks}
        for key, a in answers.items():
            if a.accepted and a.accepted[0] not in options.get(key, []):
                err("key", f"Blank {key}: answer is not one of its options.")
            if len(options.get(key, [])) < 3:
                err("blanks", f"Blank {key}: needs 3+ options.")
    if qtype.engine == E.FIB_DRAG:
        for key, a in answers.items():
            if a.accepted and a.accepted[0] not in c.bank:
                err("key", f"Blank {key}: answer is not in the word bank.")
        if len(c.bank) <= len(placeholders):
            err("bank", "Word bank needs distractors (more words than blanks).")
    if qtype.engine == E.FIB_TEXT:
        spoken = norm(script_text(c.stimulus))
        for key, a in answers.items():
            if spoken and not any(norm(v) in spoken for v in a.accepted):
                err("answerable", f"Blank {key}: answer not heard in the script.")


def student_text(contract):
    """Text used for dedup: what the student reads or hears."""
    s = contract.stimulus
    parts = [s.passage, script_text(s)]
    for name in ("prompt", "text", "spoken", "sentence", "read_text", "context"):
        parts.append(getattr(contract, name, "") or "")
    for name in ("items",):
        parts += [i.text for i in getattr(contract, name, []) or []]
    parts += [o.text for o in getattr(contract, "options", []) or []]
    parts += getattr(contract, "paragraphs", []) or []
    parts += getattr(contract, "questions", []) or []
    cue = getattr(contract, "cue_card", None)
    if cue:
        parts += [cue.topic, *cue.points]
    if s.chart:
        parts.append(s.chart.title + " " + " ".join(s.chart.categories))
    return "\n".join(p for p in parts if p)
