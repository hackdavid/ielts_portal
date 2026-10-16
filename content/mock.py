"""Deterministic MOCK providers: used when no LLM key is set.

Output is valid but meaningless filler, always flagged `is_mock`, so the whole
pipeline (validation, dedup, TTS, charts, R2, admin) can run offline.
"""

import random
import re

from catalog.models import Exam

from . import contracts as C
from .prompts import WRITING_WORDS, Analysis, Finding, Plan, PlannedBrief, Review

NOUNS = (
    "network council budget survey harbour library festival museum orchard "
    "factory reservoir campus clinic railway market studio garden bridge ferry "
    "laboratory workshop archive stadium bakery theatre canal"
).split()
ADJS = (
    "local modern rural coastal seasonal private public historic digital quiet "
    "busy annual regional temporary practical"
).split()
VERBS = (
    "expanded reduced funded replaced redesigned surveyed opened delayed "
    "improved doubled monitored promoted"
).split()
PLACES = "Northfield Ashby Kelmarsh Brindle Hartwell Oakmere Penrose Wexley".split()
NAMES = "Delgado Patel Okafor Lindqvist Moreau Tanaka Brennan Kowalski".split()
TOPICS = [
    ("Urban transport", "cycle lanes"),
    ("Environment", "wetland restoration"),
    ("Health", "sleep research"),
    ("Technology", "battery recycling"),
    ("Education", "outdoor classrooms"),
    ("Work", "four-day week trials"),
    ("Food", "vertical farming"),
    ("History", "canal engineering"),
    ("Science", "bird migration"),
    ("Culture", "community theatre"),
    ("Tourism", "eco-lodges"),
    ("Economics", "local currencies"),
]
TYPE_HINTS = [
    (r"TRUE.{0,10}FALSE.{0,10}NOT GIVEN", "R_TFNG"),
    (r"YES.{0,10}NO.{0,10}NOT GIVEN", "R_YNNG"),
    (r"(?i)list of headings|correct heading", "R_HEAD"),
    (r"(?i)label the (map|plan)", "L_MAP"),
    (r"(?i)complete the (form|notes|table)", "L_FORM"),
    (r"(?i)complete the summary", "R_SUMM"),
    (r"(?i)choose the correct letter", "R_MCQ"),
    (r"(?i)read aloud", "RA"),
    (r"(?i)repeat (the )?sentence", "RS"),
    (r"(?i)describe (the )?image", "DI"),
    (r"(?i)write from dictation", "WFD"),
    (r"(?i)re-?order", "RO"),
    (r"(?i)highlight incorrect words", "HIW"),
    (r"(?i)summari[sz]e (the )?written text", "SWT"),
    (r"(?i)essay|to what extent", "TASK2"),
]


class Gen:
    def __init__(self, seed):
        self.r = random.Random(seed)

    def pick(self, seq):
        return self.r.choice(seq)

    def sentence(self, topic):
        r = self.r
        return (
            f"In {r.choice(PLACES)}, the {r.choice(ADJS)} {r.choice(NOUNS)} linked "
            f"to {topic.lower()} was {r.choice(VERBS)} in {r.randint(1950, 2024)}, "
            f"and about {r.randint(2, 98)} per cent of {r.choice(NOUNS)} users "
            f"noticed the {r.choice(ADJS)} {r.choice(NOUNS)}."
        )

    def text(self, topic, target):
        out = []
        while len(C.words(" ".join(out))) < target:
            out.append(self.sentence(topic))
        return " ".join(out)


def _target(bounds, default=120):
    if not bounds:
        return default
    lo, hi = bounds
    return (lo + hi) // 2 if hi < 200 else lo + (hi - lo) // 4


def analyse(pages, qtypes):
    codes = {qt.code for qt in qtypes}
    found = {}
    for page in pages:
        for pattern, code in TYPE_HINTS:
            match = re.search(pattern, page.text)
            if match and code in codes:
                f = found.setdefault(
                    code,
                    Finding(
                        question_type_code=code,
                        detected_label=f"[mock] {match.group(0)[:60]}",
                        instructions_wording=page.text[
                            max(0, match.start() - 40) : match.end() + 80
                        ].strip()[:200],
                    ),
                )
                f.page_refs.append(page.page_no)
    return Analysis(findings=list(found.values()))


def plan(job, existing):
    hints = [h.strip() for h in job.topic_hints.splitlines() if h.strip()]
    pool = [(h, f"angle {i + 1}") for i, h in enumerate(hints)] + TOPICS
    taken = {t.lower() for t in existing}
    pool = [p for p in pool if f"{p[0]} / {p[1]}".lower() not in taken] or pool
    mix = [int(k) for k, v in (job.difficulty_mix or {}).items() for _ in range(v)]
    briefs = []
    for i in range(job.count):
        topic, sub = pool[(i + job.pk) % len(pool)]
        briefs.append(
            PlannedBrief(
                topic=topic,
                subtopic=sub,
                difficulty=mix[i] if i < len(mix) else 3,
                angle=f"[mock] {sub} in a mid-sized town",
            )
        )
    return Plan(briefs=briefs)


def write(qtype, brief, seed):
    g = Gen(f"{seed}:{brief.topic}:{brief.subtopic}")
    pol = C.policy_for(qtype)
    kind = C.contract_kind(qtype)
    stim = pol.get("stimulus")
    title = f"[MOCK] {qtype.code}: {brief.topic} – {brief.subtopic} #{seed}"
    base = {
        "title": title,
        "topic": brief.topic,
        "subtopic": brief.subtopic,
        "difficulty": brief.difficulty,
        "instructions": f"[mock] Instructions for {qtype.name}.",
    }
    facts = [g.sentence(brief.topic) for _ in range(6)]
    keywords = [g.pick(NOUNS) + str(i) for i in range(8)]
    body = g.text(brief.topic, _target(pol.get("words")))
    stimulus = C.StimulusSpec(title=f"{brief.topic}: {brief.subtopic}")
    if stim == "passage":
        stimulus.passage = body
    elif stim in ("audio", "map"):
        stimulus.script = _turns(body, pol.get("voices", 1))
    elif stim == "chart":
        stimulus.chart = _chart(g, brief)
    if stim == "map":
        stimulus.image_prompt = (
            f"Top-down plan of a park about {brief.subtopic}, no text"
        )
        stimulus.map_labels = [
            C.MapLabel(letter=ch, x=0.15 + 0.11 * i, y=0.3 + 0.07 * (i % 3))
            for i, ch in enumerate("ABCDEFG")
        ]
    if pol.get("image"):
        stimulus.image_prompt = f"Labelled-free diagram of {brief.subtopic}"

    if kind == "items":
        return _items(qtype, pol, base, stimulus, keywords, g)
    if kind == "mcq":
        opts = [C.Option(id=x, text=f.split(",")[0]) for x, f in zip("abcde", facts)]
        multi = qtype.engine == C.E.MCQ_MULTI
        return C.McqContract(
            **base,
            stimulus=stimulus,
            prompt=f"[mock] Which statements about {brief.subtopic} are made?",
            options=opts,
            correct=["a", "c"] if multi else ["b"],
            explanation="[mock] filler",
        )
    if kind == "inline":
        return _inline(qtype, pol, base, stimulus, keywords, g, brief)
    if kind == "reorder":
        return C.ReorderContract(**base, paragraphs=facts[:4])
    if kind == "hiw":
        spoken = g.text(brief.topic, 60).split()
        shown = list(spoken)
        for i in (3, 11, 20):
            shown[i] = "something"
        return C.HiwContract(**base, spoken=" ".join(spoken), shown=" ".join(shown))
    if kind == "dictation":
        sentence = f"The {g.pick(ADJS)} {g.pick(NOUNS)} near {g.pick(PLACES)} opens"
        sentence += f" every {g.pick(['Monday', 'Friday', 'weekend'])} morning."
        return C.DictationContract(**base, sentence=sentence)
    if kind == "writing":
        lo, hi = WRITING_WORDS.get(qtype.code, (150, None))
        return C.WritingContract(
            **base,
            stimulus=stimulus,
            prompt=f"[mock] Write about {brief.subtopic}. " + facts[0],
            min_words=lo,
            max_words=hi,
            model_answer=g.text(brief.topic, lo or 50),
        )
    prep, rec = C.SPEAKING_TIMES.get(qtype.code, (0, 40))
    extra = {}
    if qtype.code == "RA":
        extra["read_text"] = " ".join(g.text(brief.topic, 50).split()[:50]) + "."
    elif qtype.code == "RS":
        line = f"The {g.pick(ADJS)} {g.pick(NOUNS)} in {g.pick(PLACES)} opens at nine."
        stimulus.script = [C.Turn(speaker="Narrator", text=line)]
    elif qtype.code == "ASQ":
        stimulus.script = [
            C.Turn(
                speaker="Narrator", text="What do you call a person who fixes pipes?"
            )
        ]
        extra["expected_answers"] = ["plumber", "a plumber"]
    elif qtype.code == "SP2":
        extra["cue_card"] = C.CueCard(
            topic=f"Describe a {brief.subtopic} project you know about.",
            points=["what it is", "where it is", "who it helps"],
            explain="and explain why it matters.",
        )
    elif qtype.code in ("SP1", "SP3"):
        n = 5 if qtype.code == "SP1" else 4
        extra["questions"] = [f"[mock] Q{i} about {brief.subtopic}?" for i in range(n)]
    return C.SpeakingContract(
        **base,
        stimulus=stimulus,
        prompt=f"[mock] Speaking task on {brief.subtopic}.",
        prep_sec=prep,
        record_sec=rec,
        **extra,
    )


def _turns(text, voices):
    sentences = re.split(r"(?<=\.)\s+", text)
    speakers = ["Speaker A", "Speaker B"][: max(1, min(voices, 2))]
    return [
        C.Turn(speaker=speakers[i % len(speakers)], text=s)
        for i, s in enumerate(sentences)
        if s
    ]


def _chart(g, brief):
    years = ["2000", "2005", "2010", "2015", "2020"]
    return C.ChartSpec(
        chart_type=g.pick(["bar", "line"]),
        title=f"[MOCK] {brief.subtopic.title()} in two towns",
        categories=years,
        series=[
            C.ChartSeries(name=p, values=[g.r.randint(10, 90) for _ in years])
            for p in g.r.sample(PLACES, 2)
        ],
        x_label="Year",
        y_label="Share",
        unit="%",
    )


def _items(qtype, pol, base, stimulus, keywords, g):
    lo, hi = pol.get("items") or (5, 5)
    n = max(lo, min(hi, 5))
    first = 1
    items, answers, extra_text = [], [], []
    engine = qtype.engine
    for i in range(n):
        num = first + i
        kw = keywords[i]
        fact = f"The {g.pick(ADJS)} code for item {num} is {kw}."
        extra_text.append(fact)
        if engine == C.E.TFNG:
            opts = C.YNNG if qtype.code == "R_YNNG" else C.TFNG
            label = [opts[0], opts[1], "NOT GIVEN"][i % 3]
            items.append(C.Item(n=num, text=f"[mock] Statement {num}.", options=opts))
            ev = fact if label != "NOT GIVEN" else ""
            answers.append(C.Answer(key=str(num), accepted=[label], evidence=ev))
        elif engine in (C.E.MCQ_SINGLE, C.E.MATCHING, C.E.MAP_LABEL):
            if qtype.code == "R_HEAD":
                opts = ["i", "ii", "iii", "iv", "v", "vi", "vii"]
            elif engine == C.E.MAP_LABEL and qtype.code == "L_MAP":
                opts = list("ABCDEFG")
            else:
                opts = [f"A {keywords[i]}", f"B {keywords[i + 1]}", f"C {kw}x"]
            items.append(C.Item(n=num, text=f"[mock] Item {num}", options=opts))
            letter = opts[i % len(opts)].split(" ")[0]
            answers.append(C.Answer(key=str(num), accepted=[letter]))
        else:
            items.append(C.Item(n=num, text=f"The code for item {num} is ____"))
            answers.append(C.Answer(key=str(num), accepted=[kw], evidence=fact))
    if stimulus.passage:
        stimulus.passage += " " + " ".join(extra_text)
    elif stimulus.script:
        stimulus.script.append(C.Turn(speaker="Speaker A", text=" ".join(extra_text)))
    return C.ItemsContract(
        **base,
        stimulus=stimulus,
        context="[mock] i A ii B iii C iv D v E vi F vii G"
        if qtype.code == "R_HEAD"
        else "",
        word_limit=2 if engine not in (C.E.TFNG,) else None,
        items=items,
        answers=answers,
    )


def _inline(qtype, pol, base, stimulus, keywords, g, brief):
    n = 4
    filler = g.text(brief.topic, _target(pol.get("text_words"), 70)).split()
    step = max(len(filler) // (n + 1), 1)
    answers, blanks = [], []
    for k in range(n):
        idx = step * (k + 1)
        word = re.sub(r"\W", "", filler[idx]) or keywords[k]
        filler[idx] = f"{{{k + 1}}}"
        answers.append(C.Answer(key=str(k + 1), accepted=[word]))
        blanks.append(
            C.Blank(
                id=str(k + 1), options=[word, *[f"{w}" for w in keywords[k : k + 3]]]
            )
        )
    text = " ".join(filler)
    extra = {}
    if qtype.engine == C.E.FIB_DROPDOWN:
        extra["blanks"] = blanks
    elif qtype.engine == C.E.FIB_DRAG:
        extra["bank"] = [a.accepted[0] for a in answers] + keywords[5:8]
    elif qtype.engine == C.E.FIB_TEXT:
        spoken = text
        for a in answers:
            spoken = spoken.replace(f"{{{a.key}}}", a.accepted[0])
        stimulus.script = [C.Turn(speaker="Lecturer", text=spoken)]
    return C.InlineFibContract(
        **base, stimulus=stimulus, text=text, answers=answers, **extra
    )


def review(contract, built):
    """[mock] echoes the key: NOT a real blind solve (flagged in the report)."""
    answers = []
    for key, value in (built.answer_key.get("answers") or {}).items():
        answers.append(
            {"key": key, "answer": value[0] if isinstance(value, list) else value}
        )
    for key, value in (built.answer_key.get("blanks") or {}).items():
        answers.append(
            {"key": key, "answer": value[0] if isinstance(value, list) else value}
        )
    if "correct" in built.answer_key:
        c = built.answer_key["correct"]
        answers.append(
            {"key": "answer", "answer": ", ".join(c) if isinstance(c, list) else c}
        )
    if "order" in built.answer_key:
        answers.append({"key": "order", "answer": ", ".join(built.answer_key["order"])})
    if "incorrect_indices" in built.answer_key:
        idx = built.answer_key["incorrect_indices"]
        answers.append({"key": "selected", "answer": ", ".join(map(str, idx))})
    return Review(answers=answers, quality=3, issues=["[mock] reviewer did not solve"])


def is_ielts(qtype):
    return qtype.exam.kind == Exam.Kind.IELTS
