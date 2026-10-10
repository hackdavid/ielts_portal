"""Item scorers: deterministic marking + a stand-in (dummy) AI scorer.

Every scorer returns an `item_score` dict:
  raw, max_raw, scaled (0-100), scorer, details[] (review rows), traits{}, band, flags[]
"""

import hashlib
import re

from catalog.models import QuestionType

E = QuestionType.Engine
AI_ENGINES = {E.WRITING_TEXT, E.SPEAKING_AUDIO}
ARTICLES = {"a", "an", "the"}
WORD = re.compile(r"[\w'’-]+")


def words(text):
    return WORD.findall(text or "")


def norm(value, cfg):
    text = re.sub(r"\s+", " ", str(value or "").lower()).strip(" .,;:!?\"'")
    parts = text.split(" ")
    if cfg.get("ignore_articles") and len(parts) > 1 and parts[0] in ARTICLES:
        text = " ".join(parts[1:])
    return text


def show(value):
    if isinstance(value, list):
        return " / ".join(str(v) for v in value) or "—"
    return str(value) if value not in (None, "") else "—"


def _result(raw, max_raw, details, scorer="det", **extra):
    scaled = round(100.0 * raw / max_raw, 1) if max_raw else 0.0
    return {
        "raw": raw,
        "max_raw": max_raw,
        "scaled": scaled,
        "scorer": scorer,
        "details": details,
        **extra,
    }


def _labels(stem):
    labels = {}
    for it in stem.get("items") or []:
        key = str(it.get("n", it.get("id")))
        labels[key] = f"{key}. {it.get('text', '')}".strip()
    for st in stem.get("statements") or []:
        labels[str(st["id"])] = f"{st['id']}. {st['text']}"
    return labels


def _option_text(stem):
    out = {}
    for opt in stem.get("options") or []:
        if isinstance(opt, dict):
            out[str(opt["id"])] = opt.get("text", opt["id"])
    return out


def matches(given, expected, cfg, limit=None):
    if isinstance(given, list):
        given = " ".join(str(g) for g in given)
    if limit and cfg.get("enforce_word_limit") and len(words(given)) > limit:
        return False
    options = expected if isinstance(expected, list) else [expected]
    value = norm(given, cfg)
    return bool(value) and any(value == norm(o, cfg) for o in options)


def _key_map(key):
    for name in ("answers", "blanks", "pairs"):
        if isinstance(key.get(name), dict):
            return key[name]
    if "correct" in key and not isinstance(key["correct"], list):
        return {"answer": key["correct"]}
    return None


def _mcq_multi(stem, key, response, cfg):
    correct = {str(c) for c in key.get("correct", [])}
    chosen = {str(c) for c in (response.get("answer") or [])}
    hits = len(correct & chosen)
    if cfg.get("multi_mcq_scheme") == "all_or_nothing":
        raw = len(correct) if chosen == correct else 0
    else:
        raw = max(0, hits - len(chosen - correct))
    text = _option_text(stem)
    row = {
        "label": "Answer",
        "given": show([text.get(c, c) for c in sorted(chosen)]),
        "expected": show([text.get(c, c) for c in sorted(correct)]),
        "correct": chosen == correct,
    }
    return _result(raw, len(correct), [row])


def _reorder(stem, key, response, cfg):
    expected = [str(i) for i in key.get("order", [])]
    given = [str(i) for i in (response.get("order") or [])]
    if cfg.get("reorder_scheme") == "exact":
        raw, max_raw = (1 if given == expected else 0), 1
    else:
        pairs = set(zip(expected, expected[1:]))
        raw = sum(1 for p in zip(given, given[1:]) if p in pairs)
        max_raw = max(len(expected) - 1, 0)
    text = {p["id"]: p["text"] for p in stem.get("paragraphs", [])}
    row = {
        "label": "Paragraph order",
        "given": show([text.get(i, i) for i in given]),
        "expected": show([text.get(i, i) for i in expected]),
        "correct": given == expected,
    }
    return _result(raw, max_raw, [row])


def _hiw(stem, key, response, cfg):
    incorrect = {int(i) for i in key.get("incorrect_indices", [])}
    chosen = {int(i) for i in (response.get("selected") or []) if str(i).isdigit()}
    hits = len(incorrect & chosen)
    raw = max(0, hits - len(chosen - incorrect))
    shown = (stem.get("transcript") or "").split()

    def pick(idx):
        return [shown[i] for i in sorted(idx) if i < len(shown)]

    row = {
        "label": "Highlighted words",
        "given": show(pick(chosen)),
        "expected": show(pick(incorrect)),
        "correct": chosen == incorrect,
    }
    return _result(raw, len(incorrect), [row])


def _lcs(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def _dictation(stem, key, response, cfg):
    ref = [w.lower() for w in words(key.get("sentence", ""))]
    hyp = [w.lower() for w in words(response.get("answer", ""))]
    if cfg.get("wfd_scheme") == "bag":
        pool = list(hyp)
        raw = 0
        for w in ref:
            if w in pool:
                pool.remove(w)
                raw += 1
    else:
        raw = _lcs(ref, hyp)
    row = {
        "label": "Sentence",
        "given": show(response.get("answer")),
        "expected": key.get("sentence", ""),
        "correct": raw == len(ref) and len(hyp) == len(ref),
    }
    return _result(raw, len(ref), [row])


def _per_question(stem, key, response, cfg):
    mapping = _key_map(key) or {}
    labels = _labels(stem)
    text = _option_text(stem)
    limit = stem.get("word_limit")
    rows, raw = [], 0
    for qkey, expected in mapping.items():
        qkey = str(qkey)
        given = response.get(qkey, "")
        ok = matches(given, expected, cfg, limit)
        raw += ok
        rows.append(
            {
                "label": labels.get(qkey) or ("Answer" if qkey == "answer" else qkey),
                "given": show(text.get(str(given), given)),
                "expected": show(
                    [text.get(str(e), e) for e in expected]
                    if isinstance(expected, list)
                    else text.get(str(expected), expected)
                ),
                "correct": ok,
            }
        )
    return _result(raw, len(mapping), rows)


def deterministic(engine, stem, key, response, cfg):
    response = response if isinstance(response, dict) else {}
    if engine == E.MCQ_MULTI:
        return _mcq_multi(stem, key, response, cfg)
    if engine == E.REORDER:
        return _reorder(stem, key, response, cfg)
    if engine == E.HIW:
        return _hiw(stem, key, response, cfg)
    if engine == E.DICTATION:
        return _dictation(stem, key, response, cfg)
    return _per_question(stem, key, response, cfg)


# ---- Stand-in AI scorer (deterministic fake; swap for a real model later) ----


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def snap_half(x):
    return int(x * 2 + 0.5) / 2


def _noise(seed, i):
    return hashlib.sha256(f"{seed}|{i}".encode()).digest()[0] % 7 - 3


def _ielts_traits(names, base, seed):
    return {
        name: snap_half(_clamp(4.0 + 3.0 * base + _noise(seed, i) * 0.25, 1, 9))
        for i, name in enumerate(names)
    }


def _pte_traits(weights, base, seed):
    return {
        name: round(_clamp(1.5 + 3.0 * base + _noise(seed, i) * 0.15, 0, 5), 1)
        for i, name in enumerate(weights)
    }


def _ai_result(traits, cfg, ielts, flags, **extra):
    if ielts:
        values = list(traits.values())
        band = snap_half(sum(values) / len(values)) if values else 0.0
        return _result(
            band, 9, [], scorer="dummy", traits=traits, band=band, flags=flags, **extra
        )
    weights = extra.pop("weights")
    raw = sum(weights[t] * traits.get(t, 0) for t in weights)
    return _result(
        round(raw, 2),
        5 * sum(weights.values()),
        [],
        scorer="dummy",
        traits=traits,
        flags=flags,
        **extra,
    )


def dummy_writing(stem, text, cfg, ielts, seed):
    count = len(words(text))
    target = stem.get("min_words") or (150 if ielts else 50)
    names = cfg["writing_traits"]
    extra = {"words": count} if ielts else {"words": count, "weights": names}
    if count == 0:
        return _ai_result({n: 0 for n in names}, cfg, ielts, ["empty"], **extra)
    base = _clamp(count / target, 0.4, 1.0)
    flags = ["under_length"] if count < target else []
    if ielts:
        traits = _ielts_traits(names, base, f"{seed}|{text}")
        if count < target:
            first = names[0]
            traits[first] = min(traits[first], 5.5)
        return _ai_result(traits, cfg, ielts, flags, **extra)
    traits = _pte_traits(names, base, f"{seed}|{text}")
    top = stem.get("max_words")
    if "form" in traits and (count < target or (top and count > top)):
        traits["form"] = 1.0
        flags.append("form_out_of_range")
    return _ai_result(traits, cfg, ielts, flags, **extra)


def dummy_speaking(stem, size_bytes, cfg, ielts, seed):
    names = cfg["speaking_traits"]
    extra = {} if ielts else {"weights": names}
    if not size_bytes:
        return _ai_result({n: 0 for n in names}, cfg, ielts, ["no_recording"], **extra)
    seconds = stem.get("talk_sec") or stem.get("record_sec") or 60
    base = _clamp(size_bytes / (seconds * cfg["speaking_bytes_per_sec"]), 0.4, 1.0)
    flags = ["short_recording"] if base <= 0.4 else []
    make = _ielts_traits if ielts else _pte_traits
    return _ai_result(
        make(names, base, f"{seed}|{size_bytes}"), cfg, ielts, flags, **extra
    )
