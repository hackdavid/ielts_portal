"""Score submitted attempts: item scores → section scores → ScoreBreakdown."""

import logging
import traceback

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from attempts.models import Attempt, AttemptItem
from catalog.models import Exam, Section

from . import engines
from .defaults import DEFAULT_VERSION, defaults_for
from .models import ScoreBreakdown, ScoringConfig

log = logging.getLogger(__name__)
SCORER_VERSIONS = {"det": "1", "dummy": "1"}
SECTION_LABELS = dict(Section.choices)
SECTION_ORDER = ["listening", "reading", "writing", "speaking"]
SCORABLE = {Attempt.Status.SUBMITTED, Attempt.Status.SCORING, Attempt.Status.FAILED}


def ensure_default_configs():
    created = 0
    for exam in Exam.objects.all():
        if not exam.scoring_configs.filter(tenant=None).exists():
            ScoringConfig.objects.create(
                exam=exam,
                version=DEFAULT_VERSION,
                is_active=True,
                weights=defaults_for(exam),
            )
            created += 1
    return created


def get_config(exam, tenant=None):
    """Return (version, weights) — tenant config, else platform, else built-in."""
    configs = exam.scoring_configs.filter(is_active=True).order_by("-created_at")
    config = (tenant and configs.filter(tenant=tenant).first()) or configs.filter(
        tenant=None
    ).first()
    weights = defaults_for(exam)
    if config is None:
        return f"{DEFAULT_VERSION}-builtin", weights
    weights.update(config.weights or {})
    return config.version, weights


def _audio_size(item):
    if not item.audio_id:
        return 0
    try:
        return item.audio.file.size
    except (OSError, ValueError):
        return 0


def score_item(item, cfg, ielts):
    stem = item.stem_snapshot or {}
    engine = stem.get("_engine", "")
    seed = f"{item.attempt_id}|{item.order}"
    if engine == engines.E.WRITING_TEXT:
        text = (item.response or {}).get("text", "")
        result = engines.dummy_writing(stem, text, cfg, ielts, seed)
    elif engine == engines.E.SPEAKING_AUDIO:
        result = engines.dummy_speaking(stem, _audio_size(item), cfg, ielts, seed)
    else:
        key = {
            k: v for k, v in (item.answer_key_snapshot or {}).items() if k != "_meta"
        }
        result = engines.deterministic(engine, stem, key, item.response, cfg)
    if not _answered(item):
        result.setdefault("flags", []).append("unanswered")
    item.item_score = result
    item.score_status = item.ScoreStatus.SCORED
    return result


def _answered(item):
    from attempts.services import has_answer

    return bool(item.audio_id) or has_answer(item.response)


def _band_lookup(table, raw):
    for minimum, band in table:
        if raw >= minimum:
            return float(band)
    return 0.0


def round_overall(x):
    """IELTS-style: .25 rounds up to .5 and .75 up to the next whole band."""
    return int(x * 2 + 0.5) / 2


def _weighted(values):
    total = sum(w for _, w in values)
    return sum(v * w for v, w in values) / total if total else 0.0


def _ielts_rollup(items, cfg):
    sections, traits = {}, {}
    for code in SECTION_ORDER:
        rows = [i for i in items if i.section_code == code]
        if not rows:
            continue
        if code in ("listening", "reading"):
            raw = sum(i.item_score["raw"] for i in rows)
            max_raw = sum(i.item_score["max_raw"] for i in rows)
            total = cfg["band_raw_total"]
            scaled = round(raw * total / max_raw) if max_raw else 0
            band = _band_lookup(cfg["band_tables"][code], scaled)
            sections[code] = {"band": band, "raw": raw, "max_raw": max_raw}
            if max_raw != total:
                sections[code]["raw_out_of_40"] = scaled
            continue
        weights = cfg.get("writing_task_weights", {}) if code == "writing" else {}
        values = [
            (i.item_score["band"], weights.get(i.question.question_type.code, 1))
            for i in rows
        ]
        sections[code] = {"band": engines.snap_half(_weighted(values))}
        names = cfg[f"{code}_traits"]
        traits[code] = {
            n: round(sum(i.item_score["traits"].get(n, 0) for i in rows) / len(rows), 1)
            for n in names
        }
    bands = [s["band"] for s in sections.values()]
    overall = round_overall(sum(bands) / len(bands)) if bands else None
    return overall, sections, None, traits or None


def pte_display(x, scale):
    value = round(scale["offset"] + scale["factor"] * x)
    return max(scale["min"], min(scale["max"], value))


def _pte_rollup(items, cfg):
    scale = cfg["pte_scale"]
    item_weights = cfg.get("item_weights", {})
    sections, raw_means = {}, []
    for code in SECTION_ORDER:
        rows = [i for i in items if i.section_code == code and i.item_score["max_raw"]]
        if not rows:
            continue
        values = [
            (i.item_score["scaled"], item_weights.get(i.question.question_type.code, 1))
            for i in rows
        ]
        mean = _weighted(values)
        sections[code] = {"score": pte_display(mean, scale), "percent": round(mean, 1)}
        raw_means.append((mean, cfg["section_weights"].get(code, 1)))
    overall = pte_display(_weighted(raw_means), scale) if raw_means else None
    enabling = {}
    for label, names in cfg["enabling"].items():
        values = [
            i.item_score["traits"][n]
            for i in items
            for n in names
            if n in (i.item_score.get("traits") or {})
        ]
        if values:
            enabling[label] = pte_display(20 * sum(values) / len(values), scale)
    return overall, sections, enabling or None, None


def _summary(item):
    score = item.item_score
    return {
        "order": item.order,
        "section": item.section_code,
        "qtype": item.question.question_type.code,
        "raw": score["raw"],
        "max_raw": score["max_raw"],
        "scaled": score["scaled"],
        "band": score.get("band"),
        "scorer": score["scorer"],
    }


def score_attempt(attempt, *, force=False):
    """Mark every item and save the ScoreBreakdown. Safe to call repeatedly."""
    with transaction.atomic():
        locked = Attempt.objects.select_for_update().get(pk=attempt.pk)
        allowed = SCORABLE | ({Attempt.Status.SCORED} if force else set())
        if locked.status not in allowed:
            return locked
        locked.status = Attempt.Status.SCORING
        locked.save(update_fields=["status", "updated_at"])
    try:
        with transaction.atomic():
            _score(locked)
    except Exception as exc:  # noqa: BLE001 — any scorer failure marks FAILED
        log.exception("Scoring failed for attempt %s", locked.pk)
        locked.status = Attempt.Status.FAILED
        locked.meta = {
            **locked.meta,
            "scoring_error": repr(exc),
            "scoring_trace": traceback.format_exc()[-2000:],
        }
        locked.save(update_fields=["status", "meta", "updated_at"])
    return locked


def _score(attempt):
    ielts = attempt.exam.kind == Exam.Kind.IELTS
    version, cfg = get_config(attempt.exam, attempt.tenant)
    items = list(attempt.items.select_related("question__question_type", "audio"))
    deterministic = [
        i for i in items if i.stem_snapshot.get("_engine") not in engines.AI_ENGINES
    ]
    ai = [i for i in items if i not in deterministic]
    for item in deterministic + ai:
        score_item(item, cfg, ielts)
    AttemptItem.objects.bulk_update(items, ["item_score", "score_status"])
    rollup = _ielts_rollup if ielts else _pte_rollup
    overall, sections, enabling, traits = rollup(items, cfg)
    ScoreBreakdown.objects.update_or_create(
        attempt=attempt,
        defaults={
            "overall": overall,
            "scale": cfg["scale"],
            "sections": sections,
            "enabling": enabling,
            "traits": traits,
            "items_summary": [_summary(i) for i in items],
            "config_version": version,
            "scorer_versions": SCORER_VERSIONS,
            "disclaimer": settings.PRACTICE_SCORE_DISCLAIMER,
        },
    )
    attempt.status = Attempt.Status.SCORED
    attempt.scored_at = timezone.now()
    attempt.meta = {
        k: v for k, v in attempt.meta.items() if not k.startswith("scoring_")
    }
    attempt.save(update_fields=["status", "scored_at", "meta", "updated_at"])
