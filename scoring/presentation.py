"""Template view models for results and answer review."""

from django.urls import reverse

from catalog.models import Section

from .services import SECTION_ORDER

LABELS = dict(Section.choices)


def overall_text(breakdown):
    if breakdown is None or breakdown.overall is None:
        return ""
    if breakdown.scale == breakdown.Scale.IELTS_BAND:
        return f"{breakdown.overall:.1f}"
    return f"{breakdown.overall:.0f}"


def section_rows(breakdown):
    rows = []
    sections = breakdown.sections or {}
    ielts = breakdown.scale == breakdown.Scale.IELTS_BAND
    for code in SECTION_ORDER:
        data = sections.get(code)
        if not data:
            continue
        if ielts:
            value = f"{data['band']:.1f}"
            detail = (
                f"{data['raw']:g} / {data['max_raw']:g} correct"
                if "raw" in data
                else "Practice estimate from criteria"
            )
            if "raw_out_of_40" in data:
                detail += f" (≈ {data['raw_out_of_40']}/40)"
        else:
            value = str(data["score"])
            detail = f"{data['percent']:g}% of available marks"
        rows.append(
            {"code": code, "label": LABELS[code], "value": value, "detail": detail}
        )
    return rows


def trait_rows(breakdown):
    return [
        {"section": LABELS.get(code, code), "traits": traits}
        for code, traits in (breakdown.traits or {}).items()
    ]


def review_items(attempt):
    out = []
    for item in attempt.items.select_related("question__question_type", "question"):
        score = item.item_score or {}
        stem = item.stem_snapshot or {}
        meta = (item.answer_key_snapshot or {}).get("_meta")
        if meta is None:
            meta = item.question.scorer_meta or {}
        recording = (
            reverse("attempts:recording", args=[attempt.pk, item.order])
            if item.audio_id
            else None
        )
        out.append(
            {
                "order": item.order,
                "section": LABELS.get(item.section_code, item.section_code),
                "qtype": stem.get("_qtype", item.question.question_type.name),
                "title": item.question.title,
                "prompt": stem.get("prompt") or stem.get("instructions"),
                "score": score,
                "details": score.get("details") or [],
                "traits": score.get("traits") or {},
                "flags": score.get("flags") or [],
                "transcript": meta.get("transcript"),
                "text": (item.response or {}).get("text")
                if score.get("words") is not None
                else None,
                "recording": recording,
            }
        )
    return out
