"""Attempt lifecycle: start (snapshot), server clock, section advance, finalize."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from catalog.models import PracticeMode, QuestionType, Section

from .models import Attempt, AttemptItem

GRACE_SEC = 5
DEFAULT_ITEM_SEC = 600
MOCK_LISTENING = {"max_plays": 1, "allow_seek": False}
PRACTICE_LISTENING = {"max_plays": 0, "allow_seek": True}
SECTION_LABELS = dict(Section.choices)


def _resume(user, key):
    return (
        Attempt.objects.filter(
            user=user, status=Attempt.Status.IN_PROGRESS, meta__resume_key=key
        )
        .order_by("-started_at")
        .first()
    )


@transaction.atomic
def _create(request, *, exam, pack, mode, section_code, sections, entries, key):
    """`entries` = [(section_code, question, time_limit_sec, part)] in play order."""
    now = timezone.now()
    first = sections[0]
    policy = (pack.navigation_policy if pack else {}) or {}
    listening = dict(
        PRACTICE_LISTENING if mode == PracticeMode.QUESTION else MOCK_LISTENING
    )
    listening.update(policy.get("listening", {}))
    attempt = Attempt.objects.create(
        user=request.user,
        tenant_id=(request.auth_context or {}).get("tenant_id"),
        exam=exam,
        pack=pack,
        mode=mode,
        section_code=section_code,
        status=Attempt.Status.IN_PROGRESS,
        started_at=now,
        server_deadline_at=now + timedelta(seconds=first["total_sec"]),
        duration_sec=sum(s["total_sec"] for s in sections),
        config_snapshot={"sections": sections, "listening": listening},
        meta={"resume_key": key, "section_index": 0},
    )
    AttemptItem.objects.bulk_create(
        AttemptItem(
            attempt=attempt,
            order=order,
            question=question,
            question_version=question.version,
            section_code=code,
            stem_snapshot={
                **question.stem,
                "_engine": question.question_type.engine,
                "_qtype": question.question_type.name,
                "_part": part,
                "_audio": question.audio.file.url if question.audio_id else None,
            },
            answer_key_snapshot=question.answer_key,
            time_limit_sec=limit,
        )
        for order, (code, question, limit, part) in enumerate(entries, start=1)
    )
    return attempt


def _section_row(code, label, duration, extra=0):
    return {
        "section": code,
        "label": label,
        "duration_sec": duration,
        "extra_sec": extra,
        "total_sec": duration + extra,
    }


def start_pack(request, pack, section=None):
    """Full mock, or one section of it (section-wise practice)."""
    mode = PracticeMode.SECTION if section else PracticeMode.FULL_MOCK
    key = f"pack:{pack.pk}:{section or 'all'}"
    if existing := _resume(request.user, key):
        return existing
    plan = [r for r in pack.section_plan() if not section or r["section"] == section]
    items = pack.items.select_related("question__question_type", "question__audio")
    by_section = {}
    for item in items.order_by("order"):
        by_section.setdefault(item.section_code, []).append(item)
    sections, entries = [], []
    for row in plan:
        rows = by_section.get(row["section"], [])
        if not rows:
            continue
        sections.append(
            _section_row(
                row["section"],
                SECTION_LABELS.get(row["section"], row["section"]),
                row["duration_sec"],
                row["extra_sec"],
            )
        )
        entries += [
            (i.section_code, i.question, i.time_override_sec, i.part) for i in rows
        ]
    if not entries:
        return None
    return _create(
        request,
        exam=pack.exam,
        pack=pack,
        mode=mode,
        section_code=section or "",
        sections=sections,
        entries=entries,
        key=key,
    )


def start_questions(request, qtype: QuestionType, questions):
    """Question-wise practice over one question or a whole question type."""
    questions = list(questions)
    if not questions:
        return None
    ids = ",".join(sorted(str(q.pk) for q in questions))
    key = f"qtype:{qtype.pk}:{ids if len(questions) == 1 else 'all'}"
    if existing := _resume(request.user, key):
        return existing
    limit = qtype.default_time_sec or DEFAULT_ITEM_SEC
    sections = [_section_row(qtype.section, qtype.name, limit * len(questions))]
    entries = [(qtype.section, q, limit, None) for q in questions]
    return _create(
        request,
        exam=qtype.exam,
        pack=None,
        mode=PracticeMode.QUESTION,
        section_code=qtype.section,
        sections=sections,
        entries=entries,
        key=key,
    )


def questions_for(qtype, queryset, question_id=None):
    qs = queryset.filter(question_type=qtype).select_related("question_type", "audio")
    if question_id:
        return qs.filter(pk=question_id)
    return qs.order_by("title")


def section_index(attempt):
    return int(attempt.meta.get("section_index", 0))


def sections(attempt):
    return attempt.config_snapshot.get("sections", [])


def current_section(attempt):
    rows = sections(attempt)
    i = section_index(attempt)
    return rows[i] if i < len(rows) else None


def current_items(attempt):
    section = current_section(attempt)
    if section is None:
        return attempt.items.none()
    return attempt.items.filter(section_code=section["section"]).order_by("order")


def finalize(attempt):
    """IN_PROGRESS → SUBMITTED. Safe to call repeatedly."""
    with transaction.atomic():
        locked = Attempt.objects.select_for_update().get(pk=attempt.pk)
        if locked.status == Attempt.Status.IN_PROGRESS:
            now = timezone.now()
            locked.status = Attempt.Status.SUBMITTED
            locked.submitted_at = now
            locked.server_deadline_at = None
            locked.save(
                update_fields=[
                    "status",
                    "submitted_at",
                    "server_deadline_at",
                    "updated_at",
                ]
            )
            locked.items.filter(submitted_at__isnull=True).update(submitted_at=now)
    attempt.refresh_from_db()
    return attempt


def advance(attempt, *, start_at=None):
    """Close the current section and open the next (or submit after the last)."""
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return attempt
    now = timezone.now()
    current_items(attempt).filter(submitted_at__isnull=True).update(submitted_at=now)
    nxt = section_index(attempt) + 1
    rows = sections(attempt)
    if nxt >= len(rows):
        return finalize(attempt)
    attempt.meta["section_index"] = nxt
    attempt.server_deadline_at = (start_at or now) + timedelta(
        seconds=rows[nxt]["total_sec"]
    )
    attempt.save(update_fields=["meta", "server_deadline_at", "updated_at"])
    return attempt


def sync_clock(attempt):
    """Trust the server deadline: roll past every section whose time (+grace) is up."""
    while (
        attempt.status == Attempt.Status.IN_PROGRESS
        and attempt.server_deadline_at
        and timezone.now() > attempt.server_deadline_at + timedelta(seconds=GRACE_SEC)
    ):
        advance(attempt, start_at=attempt.server_deadline_at)
    return attempt


def has_answer(value):
    if isinstance(value, dict):
        return any(has_answer(v) for v in value.values())
    if isinstance(value, list):
        return any(has_answer(v) for v in value)
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def needs_mic_check(attempt):
    return (
        not attempt.meta.get("mic_checked")
        and attempt.items.filter(
            question__question_type__engine=QuestionType.Engine.SPEAKING_AUDIO
        ).exists()
    )
