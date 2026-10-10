"""Rule-based skill profile and "next step" for the student dashboard.

Picks the weakest question type from recent scored attempts. This is the
seam the adaptive engine will replace; nothing here is presented as AI.
"""

from collections import defaultdict

from django.urls import reverse

from attempts.models import Attempt
from catalog.demo import SECTION_ORDER
from catalog.models import Section
from scoring.models import ScoreBreakdown

LABELS = dict(Section.choices)
RECENT = 10
IELTS = ScoreBreakdown.Scale.IELTS_BAND


def _avg(values):
    return sum(values) / len(values)


def _fmt(scale, value):
    if scale == IELTS:
        return f"{round(value * 2) / 2:.1f}"
    return f"{round(value)}"


def _to_pct(scale, value):
    pct = value / 9 * 100 if scale == IELTS else (value - 10) / 80 * 100
    return max(0, min(100, round(pct)))


def _item_pct(item):
    if item.get("band") is not None:
        return float(item["band"]) / 9 * 100
    if item.get("max_raw"):
        return float(item["raw"]) / float(item["max_raw"]) * 100
    return None


def _sparkline(scale, values, width=120, height=40):
    if len(values) < 2:
        return None
    pcts = [_to_pct(scale, v) for v in values]
    step = width / (len(pcts) - 1)
    points = [
        (round(i * step, 1), round(height - 4 - p * (height - 8) / 100, 1))
        for i, p in enumerate(pcts)
    ]
    return {
        "points": " ".join(f"{x},{y}" for x, y in points),
        "area": f"0,{height} "
        + " ".join(f"{x},{y}" for x, y in points)
        + f" {width},{height}",
        "last": points[-1],
    }


def skill_profile(user, exam):
    breakdowns = list(
        ScoreBreakdown.objects.filter(
            attempt__user=user,
            attempt__exam=exam,
            attempt__status=Attempt.Status.SCORED,
        ).order_by("-attempt__submitted_at")[:RECENT]
    )
    scale = (
        breakdowns[0].scale
        if breakdowns
        else (
            IELTS
            if exam.kind == exam.Kind.IELTS
            else next(s for s in ScoreBreakdown.Scale if s != IELTS)
        )
    )
    per_section, per_qtype = defaultdict(list), defaultdict(list)
    for b in breakdowns:
        for code, data in (b.sections or {}).items():
            value = data.get("band") if b.scale == IELTS else data.get("score")
            if value is not None:
                per_section[code].append(float(value))
        for item in b.items_summary or []:
            pct = _item_pct(item)
            if pct is not None:
                per_qtype[item["qtype"]].append(pct)
    skills = [
        {
            "code": code,
            "label": LABELS[code],
            "display": _fmt(scale, _avg(per_section[code])),
            "pct": _to_pct(scale, _avg(per_section[code])),
            "count": len(per_section[code]),
        }
        for code in SECTION_ORDER.get(exam.kind, [c for c, _ in Section.choices])
        if per_section.get(code)
    ]
    weakest_qtype = None
    if per_qtype:
        code, values = min(per_qtype.items(), key=lambda kv: _avg(kv[1]))
        qtype = exam.question_types.filter(code=code).first()
        if qtype:
            weakest_qtype = {
                "type": qtype,
                "pct": round(_avg(values)),
                "count": len(values),
            }
    overall = [float(b.overall) for b in reversed(breakdowns) if b.overall is not None]
    return {
        "scale": scale,
        "is_band": scale == IELTS,
        "skills": skills,
        "weakest_section": min(skills, key=lambda s: s["pct"]) if skills else None,
        "weakest_qtype": weakest_qtype,
        "scored_count": len(breakdowns),
        "latest": _fmt(scale, overall[-1]) if overall else None,
        "best": _fmt(scale, max(overall)) if overall else None,
        "trend": _sparkline(scale, overall),
    }


def next_step(profile, exam, in_progress, packs):
    if in_progress:
        attempt = in_progress[0]
        return {
            "kind": "resume",
            "eyebrow": "Pick up where you left off",
            "title": attempt.pack.title if attempt.pack else attempt.exam.name,
            "meta": attempt.get_mode_display(),
            "body": (
                "Your attempt is still open. The clock is kept on the server, so "
                "check how much time is left."
            ),
            "url": reverse("attempts:play", args=[attempt.pk]),
            "cta": "Resume",
        }
    weakest = profile["weakest_qtype"]
    if weakest:
        qtype = weakest["type"]
        attempts = "attempt" if weakest["count"] == 1 else "attempts"
        return {
            "kind": "focus",
            "eyebrow": "Your next step",
            "title": qtype.name,
            "meta": qtype.get_section_display(),
            "pct": weakest["pct"],
            "body": (
                f"You scored {weakest['pct']}% on {qtype.name} across "
                f"{weakest['count']} recent {attempts}, your lowest question type "
                "right now. That's where practice pays off next."
            ),
            "url": reverse("catalog:qtype_list", args=[exam.slug, qtype.code]),
            "cta": "Start drill",
        }
    pack = next((p for p in packs if not getattr(p, "locked", False)), None)
    if pack:
        return {
            "kind": "diagnose",
            "eyebrow": "Find your level",
            "title": pack.title,
            "meta": "Full mock",
            "body": (
                "Take one full mock first. Every answer is scored, so your next steps "
                "come from where you actually stand."
            ),
            "url": reverse("catalog:mock_detail", args=[pack.pk]),
            "cta": "See the mock",
        }
    return {
        "kind": "browse",
        "eyebrow": "Get started",
        "title": exam.name,
        "meta": "Practice",
        "body": "Pick a section or question type to start building your score profile.",
        "url": reverse("catalog:exam_detail", args=[exam.slug]),
        "cta": "Browse practice",
    }
