"""Draft → Stimulus + Question, in one transaction. Nothing is live before this."""

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Question, Stimulus, Tag

from . import dedup
from .contracts import POLICIES
from .models import DraftQuestion, Embedding, GenerationJob, JobStep, MediaRequest

STIMULUS_KIND = {
    "passage": Stimulus.Kind.READING_PASSAGE,
    "audio": Stimulus.Kind.LISTENING_SCRIPT,
    "map": Stimulus.Kind.LISTENING_SCRIPT,
    "chart": Stimulus.Kind.IMAGE,
    "image": Stimulus.Kind.IMAGE,
}


class PublishError(Exception):
    pass


def blockers(draft, force=False):
    out = []
    if draft.status == draft.Status.PUBLISHED:
        out.append("Already published.")
    if draft.status not in (draft.Status.READY, draft.Status.NEEDS_REVISION):
        out.append(f"Status is “{draft.get_status_display()}”.")
    if any(i["level"] == "error" for i in draft.validation.get("issues", [])):
        out.append("Validation errors.")
    if draft.media.exclude(status=MediaRequest.Status.DONE).exists():
        out.append("Media not finished.")
    if draft.is_mock and not (settings.DEBUG or settings.CONTENT_ALLOW_MOCK_PUBLISH):
        out.append("Mock content can only be published in DEBUG.")
    if not force:
        if draft.verdict in ("duplicate", "copy_risk"):
            out.append(f"Dedup verdict: {draft.get_verdict_display()}.")
        if draft.review.get("agreement", 1) < 1:
            out.append("Reviewer disagreed with the key.")
    return out


@transaction.atomic
def publish(draft, user=None, force=False):
    draft = DraftQuestion.objects.select_for_update().get(pk=draft.pk)
    problems = blockers(draft, force)
    if problems:
        raise PublishError(" ".join(problems))
    job, qtype = draft.job, draft.question_type
    media = {m.kind: m.asset for m in draft.media.select_related("asset")}
    image = media.get("chart") or media.get("map") or media.get("image")
    s = draft.stimulus or {}
    stimulus = None
    kind = POLICIES.get(qtype.code, {}).get("stimulus")
    body = s.get("passage") or script_text_from(s)
    if body or image or media.get("audio"):
        stimulus = Stimulus.objects.create(
            exam=job.exam,
            kind=STIMULUS_KIND.get(kind, Stimulus.Kind.TEXT),
            title=(s.get("title") or draft.title)[:200],
            body=body,
            script=s.get("script") or [],
            meta={"chart": s.get("chart"), "map_labels": s.get("map_labels")},
            audio=media.get("audio"),
            image=image,
            content_hash=dedup.content_hash(qtype.code, body) if body else "",
        )
    topic = None
    if draft.topic:
        topic, _ = Tag.objects.get_or_create(
            slug=slugify(draft.topic)[:50] or "topic",
            defaults={"label": draft.topic[:80]},
        )
    question = Question.objects.create(
        exam=job.exam,
        question_type=qtype,
        title=draft.title,
        difficulty=draft.difficulty,
        stem=draft.stem,
        answer_key=draft.answer_key,
        scorer_meta=draft.scorer_meta,
        explanations=draft.explanations,
        stimulus=stimulus,
        audio=media.get("audio"),
        origin=Question.Origin.GENERATED,
        pool=Question.Pool.MOCK
        if job.target_pool == GenerationJob.Target.MOCK
        else Question.Pool.PRACTICE,
        topic=topic,
        subtopic=draft.subtopic,
        content_hash=draft.content_hash,
        minhash=draft.minhash,
    )
    if topic:
        question.tags.add(topic)
    question.assets.add(*[a for a in media.values() if a])
    Embedding.objects.filter(owner_type="draft", owner_id=str(draft.pk)).update(
        owner_type="question", owner_id=str(question.pk)
    )
    draft.published_question = question
    draft.published_stimulus = stimulus
    draft.status = draft.Status.PUBLISHED
    draft.save(
        update_fields=[
            "published_question",
            "published_stimulus",
            "status",
            "updated_at",
        ]
    )
    JobStep.objects.create(
        job=job,
        draft=draft,
        agent=JobStep.Agent.PUBLISH,
        provider="admin",
        input={"user": str(user) if user else "", "force": force},
        output={"question": str(question.pk), "pool": question.pool},
    )
    if not job.drafts.exclude(
        status__in=[draft.Status.PUBLISHED, draft.Status.REJECTED]
    ).exists():
        job.status = job.Status.DONE
        job.save(update_fields=["status", "updated_at"])
    return question


def script_text_from(stimulus):
    turns = stimulus.get("script") or []
    if not turns:
        return ""
    return "\n".join(f"{t['speaker']}: {t['text']}" for t in turns)
