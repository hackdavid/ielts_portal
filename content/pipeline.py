"""Deterministic orchestration. Agents only do analyse / plan / write / review.

Each stage records a JobStep (input, output, provider, tokens, latency, error),
so a failed run can be inspected step by step and retried from where it stopped.
"""

import hashlib
import io
import json
import logging
import threading
import time
from contextlib import contextmanager
from decimal import Decimal

from django.conf import settings
from django.db import close_old_connections
from django.db.models import Q

from catalog.models import Asset, Question

from . import contracts as C
from . import dedup, embeddings, llm, mock
from .assets import save_asset
from .media import charts, images, tts
from .models import (
    DraftQuestion,
    GenerationJob,
    JobStep,
    MediaRequest,
    PatternProfile,
    QuestionBrief,
    SimilarityHit,
    SourceDocument,
    SourcePage,
)
from .prompts import (
    ANALYST,
    EXTRA,
    PLANNER,
    REVIEWER,
    STIMULUS_RULES,
    WRITER,
    WRITING_WORDS,
    Analysis,
    Plan,
    Review,
)

log = logging.getLogger(__name__)
PAGE_CHARS = 3500
MAX_WRITE_TRIES = 3
SOLVABLE = ("items", "mcq", "inline", "reorder", "hiw")


# ---------------------------------------------------------------- tracing


@contextmanager
def step(agent, *, job=None, document=None, draft=None, payload=None):
    rec = JobStep(
        job=job,
        document=document,
        draft=draft,
        agent=agent,
        input=_jsonable(payload or {}),
    )
    started = time.monotonic()
    try:
        yield rec
    except Exception as exc:
        rec.ok = False
        rec.error = f"{type(exc).__name__}: {exc}"[:4000]
        raise
    finally:
        rec.latency_ms = rec.latency_ms or int((time.monotonic() - started) * 1000)
        rec.output = _jsonable(rec.output)
        rec.save()


def _jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return json.loads(json.dumps(value, default=str))


def _record_llm(rec, result, job=None):
    rec.provider = f"{result.provider}:{result.model}"
    rec.tokens_in, rec.tokens_out = result.tokens_in, result.tokens_out
    rec.latency_ms = result.latency_ms
    rec.output = result.output.model_dump()
    if job is not None:
        GenerationJob.objects.filter(pk=job.pk).update(
            tokens_in=job.tokens_in + result.tokens_in,
            tokens_out=job.tokens_out + result.tokens_out,
            spent_usd=job.spent_usd + Decimal(str(round(result.cost, 4))),
        )
        job.refresh_from_db(fields=["tokens_in", "tokens_out", "spent_usd"])


# ---------------------------------------------------------------- sources


def _chunks(text):
    paras, buf, out = text.split("\n"), "", []
    for para in paras:
        if len(buf) + len(para) > PAGE_CHARS and buf:
            out.append(buf)
            buf = ""
        buf += para + "\n"
    if buf.strip():
        out.append(buf)
    return out


def extract_document(doc):
    """File / pasted text → SourcePage rows (with MinHash for the copy guard)."""
    with step("extract", document=doc, payload={"title": doc.title}) as rec:
        if doc.file:
            doc.file.open("rb")
            data = doc.file.read()
            doc.file.close()
        else:
            data = doc.pasted_text.encode()
        doc.sha256 = hashlib.sha256(data).hexdigest()
        twin = SourceDocument.objects.filter(sha256=doc.sha256).exclude(pk=doc.pk)
        if twin.exists():
            doc.status, doc.error = doc.Status.FAILED, f"Duplicate of “{twin.first()}”."
            doc.save(update_fields=["sha256", "status", "error", "updated_at"])
            rec.output = {"duplicate_of": twin.first().pk}
            return doc
        name = (doc.file.name or "").lower()
        if name.endswith(".pdf"):
            from pypdf import PdfReader

            texts = [p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages]
        elif name.endswith(".docx"):
            import docx

            body = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
            texts = _chunks(body)
        else:
            texts = _chunks(data.decode("utf-8", errors="replace"))
        doc.pages.all().delete()
        SourcePage.objects.bulk_create(
            SourcePage(document=doc, page_no=i, text=t, minhash=dedup.minhash(t))
            for i, t in enumerate(texts, start=1)
        )
        doc.page_count = len(texts)
        doc.status, doc.error = doc.Status.EXTRACTED, ""
        doc.save(
            update_fields=["sha256", "page_count", "status", "error", "updated_at"]
        )
        rec.provider = "pypdf" if name.endswith(".pdf") else "text"
        rec.output = {"pages": len(texts), "chars": sum(len(t) for t in texts)}
    return doc


def analyse_document(doc):
    """Analyst agent → PatternProfile rows (status proposed, approve in admin)."""
    if doc.status == doc.Status.UPLOADED:
        extract_document(doc)
    pages = list(doc.pages.all())
    qtypes = list(doc.exam.question_types.all())
    payload = {
        "exam": doc.exam.name,
        "question_types": [
            {"code": q.code, "name": q.name, "section": q.section, "engine": q.engine}
            for q in qtypes
        ],
        "pages": [{"page": p.page_no, "text": p.text[:PAGE_CHARS]} for p in pages],
    }
    with step("analyst", document=doc, payload={"pages": len(pages)}) as rec:
        if llm.enabled():
            result = llm.run("analyst", ANALYST, payload, Analysis)
            _record_llm(rec, result)
            analysis = result.output
        else:
            analysis = mock.analyse(pages, qtypes)
            rec.provider, rec.output = "mock", analysis.model_dump()
    by_code = {q.code: q for q in qtypes}
    made = []
    for f in analysis.findings:
        made.append(
            PatternProfile.objects.create(
                document=doc,
                exam=doc.exam,
                question_type=by_code.get(f.question_type_code or ""),
                detected_label=f.detected_label[:200],
                spec=f.model_dump(),
                page_refs=f.page_refs,
            )
        )
    doc.status = doc.Status.ANALYSED
    doc.save(update_fields=["status", "updated_at"])
    return made


# ---------------------------------------------------------------- jobs


def run_job(job):
    """Plan → (write → validate → review → dedup → media) per brief. Resumable."""
    job.status, job.error = job.Status.RUNNING, ""
    job.is_mock = not llm.enabled()
    job.save(update_fields=["status", "error", "is_mock", "updated_at"])
    sync_type_schema(job.question_type)
    try:
        if not job.briefs.exists():
            plan_job(job)
        for brief in job.briefs.filter(status=QuestionBrief.Status.PLANNED):
            if job.spent_usd >= job.budget_usd:
                raise RuntimeError(f"Budget ${job.budget_usd} reached.")
            try:
                draft = write_draft(job, brief)
                process_draft(draft)
            except Exception:
                log.exception("brief %s failed", brief.pk)
                brief.status = brief.Status.FAILED
                brief.save(update_fields=["status"])
        for draft in job.drafts.filter(status=DraftQuestion.Status.MEDIA_PENDING):
            make_media(draft)
    except Exception as exc:
        job.status, job.error = job.Status.FAILED, str(exc)[:2000]
        job.save(update_fields=["status", "error", "updated_at"])
        return job
    ready = job.drafts.filter(status=DraftQuestion.Status.READY).exists()
    job.status = job.Status.REVIEW if ready else job.Status.FAILED
    if not ready:
        job.error = "No draft passed; see steps."
    job.save(update_fields=["status", "error", "updated_at"])
    return job


def start_in_background(job_id):
    def target():
        close_old_connections()
        try:
            run_job(GenerationJob.objects.get(pk=job_id))
        finally:
            close_old_connections()

    threading.Thread(target=target, daemon=True, name=f"content-job-{job_id}").start()


def sync_type_schema(qtype):
    schema = C.json_schema(qtype)
    policy = {k: v for k, v in C.POLICIES.get(qtype.code, {}).items()}
    policy = json.loads(json.dumps(policy))
    if qtype.content_schema != schema or (not qtype.media_policy and policy):
        qtype.content_schema = schema
        qtype.media_policy = qtype.media_policy or policy
        qtype.save(update_fields=["content_schema", "media_policy"])


def bank_topics(qtype):
    rows = Question.objects.filter(question_type=qtype).values_list(
        "topic__label", "subtopic", "title"
    )
    drafts = DraftQuestion.objects.filter(question_type=qtype).exclude(
        status=DraftQuestion.Status.REJECTED
    )
    out = [f"{t} / {s}" if t else title for t, s, title in rows]
    out += [f"{d.topic} / {d.subtopic}" for d in drafts]
    return sorted(set(out))[:300]


def plan_job(job):
    existing = bank_topics(job.question_type)
    payload = {
        "exam": job.exam.name,
        "question_type": {
            "code": job.question_type.code,
            "name": job.question_type.name,
        },
        "count": job.count,
        "difficulty_mix": job.difficulty_mix or {"3": job.count},
        "topic_hints": [h for h in job.topic_hints.splitlines() if h.strip()],
        "existing_topics": existing,
        "patterns": [p.spec for p in job.profiles.all()],
    }
    with step("planner", job=job, payload=payload) as rec:
        if llm.enabled():
            result = llm.run("planner", PLANNER, payload, Plan, model=job.llm_model)
            _record_llm(rec, result, job)
            plan = result.output
        else:
            plan = mock.plan(job, existing)
            rec.provider, rec.output = "mock", plan.model_dump()
    taken = {t.lower() for t in existing}
    for b in plan.briefs[: job.count]:
        label = f"{b.topic} / {b.subtopic}".lower()
        QuestionBrief.objects.create(
            job=job,
            topic=b.topic[:120],
            subtopic=b.subtopic[:120],
            difficulty=min(max(b.difficulty, 1), 5),
            angle=b.angle[:300],
            status=QuestionBrief.Status.DUPLICATE
            if label in taken
            else QuestionBrief.Status.PLANNED,
        )
        taken.add(label)


def _writer_prompt(qtype, job):
    pol = C.policy_for(qtype)
    extra = EXTRA.get(qtype.code, "")
    if qtype.code in WRITING_WORDS:
        lo, hi = WRITING_WORDS[qtype.code]
        extra += f"\nmin_words={lo}, max_words={hi}."
    if qtype.code in C.SPEAKING_TIMES:
        prep, rec = C.SPEAKING_TIMES[qtype.code]
        extra += f"\nprep_sec={prep}, record_sec={rec}."
    return WRITER.format(
        exam=job.exam.name,
        code=qtype.code,
        name=qtype.name,
        stimulus_rule=STIMULUS_RULES.get(pol.get("stimulus")),
        first_item=1,
        policy=json.dumps(pol),
        extra=extra,
    )


def write_draft(job, brief, feedback=None, revision_of=None):
    """Writer agent with a validate-and-retry loop (max MAX_WRITE_TRIES)."""
    qtype = job.question_type
    cls = C.contract_for(qtype)
    payload = {
        "brief": {
            "topic": brief.topic,
            "subtopic": brief.subtopic,
            "difficulty": brief.difficulty,
            "angle": brief.angle,
        },
        "patterns": [p.spec for p in job.profiles.all()],
    }
    if feedback:
        payload["fix_these_problems"] = feedback
    issues, contract, recs = [], None, []
    for attempt in range(1, MAX_WRITE_TRIES + 1):
        with step("writer", job=job, payload={**payload, "try": attempt}) as rec:
            recs.append(rec)
            if llm.enabled():
                model = settings.CONTENT_LLM_WRITER_MODEL or job.llm_model
                result = llm.run(
                    "writer", _writer_prompt(qtype, job), payload, cls, model
                )
                _record_llm(rec, result, job)
                contract = result.output
            else:
                contract = mock.write(qtype, brief, f"{job.pk}-{brief.pk}-{attempt}")
                rec.provider, rec.output = "mock", contract.model_dump()
        issues = C.check(contract, qtype)
        errors = [i for i in issues if i["level"] == "error"]
        with step("validate", job=job, payload={"try": attempt}) as rec:
            recs.append(rec)
            rec.output = {"issues": issues}
            rec.ok = not errors
        if not errors:
            break
        payload["fix_these_problems"] = [i["message"] for i in errors]
        payload["previous_attempt"] = contract.model_dump()
    built = C.build(contract, qtype)
    text = C.student_text(contract)
    draft = DraftQuestion.objects.create(
        job=job,
        brief=None if revision_of else brief,
        question_type=qtype,
        title=contract.title[:200],
        topic=contract.topic[:120],
        subtopic=contract.subtopic[:120],
        difficulty=contract.difficulty,
        contract=contract.model_dump(),
        stimulus=contract.stimulus.model_dump(),
        stem=built.stem,
        answer_key=built.answer_key,
        scorer_meta=built.scorer_meta,
        explanations=built.explanations,
        validation={"issues": issues, "tries": attempt},
        content_hash=dedup.content_hash(qtype.code, text),
        minhash=dedup.minhash(text),
        is_mock=not llm.enabled(),
        revision_of=revision_of,
        status=DraftQuestion.Status.DRAFTED,
    )
    JobStep.objects.filter(pk__in=[r.pk for r in recs]).update(draft=draft)
    if not revision_of:
        brief.status = brief.Status.WRITTEN
        brief.save(update_fields=["status"])
    return draft


def process_draft(draft):
    errors = [i for i in draft.validation.get("issues", []) if i["level"] == "error"]
    review_draft(draft)
    check_duplicates(draft)
    if errors or draft.review.get("agreement", 1) < 1:
        draft.status = draft.Status.NEEDS_REVISION
        draft.save(update_fields=["status", "updated_at"])
    plan_media(draft)
    if draft.status != draft.Status.NEEDS_REVISION:
        make_media(draft)


def contract_of(draft):
    return C.contract_for(draft.question_type).model_validate(draft.contract)


def _student_payload(draft, contract):
    payload = {"stem": draft.stem}
    if contract.stimulus.script:
        payload["audio_script"] = C.script_text(contract.stimulus)
    if isinstance(contract, C.HiwContract):
        payload["audio_script"] = contract.spoken
    if isinstance(contract, C.ReorderContract):
        payload["task"] = "Give the paragraph ids in the correct order as key 'order'."
    if isinstance(contract, C.HiwContract):
        payload["task"] = (
            "Give 0-based indices of shown words that differ (key 'selected')."
        )
    if isinstance(contract, C.McqContract):
        payload["task"] = "Give option id(s) as key 'answer'."
    return payload


def review_draft(draft):
    """Reviewer solves blind (no key); disagreement → needs revision."""
    contract = contract_of(draft)
    kind = C.contract_kind(draft.question_type)
    payload = _student_payload(draft, contract)
    with step("reviewer", job=draft.job, draft=draft, payload=payload) as rec:
        if llm.enabled():
            result = llm.run(
                "reviewer", REVIEWER, payload, Review, model=draft.job.llm_model
            )
            _record_llm(rec, result, draft.job)
            review = result.output
        else:
            review = mock.review(contract, C.build(contract, draft.question_type))
            rec.provider, rec.output = "mock", review.model_dump()
    disagreements = _compare(kind, draft.answer_key, review) if kind in SOLVABLE else []
    total = max(len(_expected(draft.answer_key)), 1)
    draft.review = {
        **review.model_dump(),
        "disagreements": disagreements,
        "agreement": round(1 - len(disagreements) / total, 3)
        if kind in SOLVABLE
        else 1,
        "blind_solved": kind in SOLVABLE,
        "mock": not llm.enabled(),
    }
    draft.save(update_fields=["review", "updated_at"])


def _expected(key):
    out = {}
    for name in ("answers", "blanks"):
        out.update({str(k): v for k, v in (key.get(name) or {}).items()})
    if "correct" in key:
        out["answer"] = key["correct"]
    if "order" in key:
        out["order"] = key["order"]
    if "incorrect_indices" in key:
        out["selected"] = [str(i) for i in key["incorrect_indices"]]
    return out


def _compare(kind, key, review):
    from scoring.engines import matches

    given = {a.key.strip(): a.answer for a in review.answers}
    cfg = {"case_insensitive": True, "trim": True}
    out = []
    for k, expected in _expected(key).items():
        got = given.get(k, "")
        if isinstance(expected, list) and k in ("answer", "order", "selected"):
            parts = [
                p.strip() for p in str(got).replace(";", ",").split(",") if p.strip()
            ]
            ok = parts == expected if k == "order" else set(parts) == set(expected)
        else:
            ok = matches(got, expected, cfg) or matches(
                str(got).split(" ")[0], expected, cfg
            )
        if not ok:
            out.append({"key": k, "expected": expected, "reviewer": got})
    return out


def check_duplicates(draft):
    """Exact → MinHash → embedding vs bank + other drafts; copy guard vs sources."""
    qtype = draft.question_type
    t = settings.CONTENT_DEDUP
    text = C.student_text(contract_of(draft))
    hits = []

    def hit(target_type, target_id, label, method, score):
        verdict = dedup.verdict_for(method, score)
        if verdict:
            hits.append(
                SimilarityHit(
                    draft=draft,
                    target_type=target_type,
                    target_id=str(target_id),
                    target_label=str(label)[:255],
                    method=method,
                    score=round(score, 4),
                    verdict=verdict,
                )
            )

    bank = Question.objects.filter(question_type=qtype).only(
        "id", "title", "content_hash", "minhash"
    )
    others = DraftQuestion.objects.filter(question_type=qtype).exclude(
        Q(pk=draft.pk) | Q(status=DraftQuestion.Status.REJECTED)
    )
    for q in bank:
        if q.content_hash and q.content_hash == draft.content_hash:
            hit("question", q.pk, q.title, "exact", 1.0)
        elif q.minhash:
            hit(
                "question",
                q.pk,
                q.title,
                "minhash",
                dedup.jaccard(q.minhash, draft.minhash),
            )
    for d in others.only("id", "title", "content_hash", "minhash"):
        if d.content_hash == draft.content_hash:
            hit("draft", d.pk, d.title, "exact", 1.0)
        elif d.minhash:
            hit(
                "draft",
                d.pk,
                d.title,
                "minhash",
                dedup.jaccard(d.minhash, draft.minhash),
            )
    vec = embeddings.store("draft", draft.pk, draft.job.exam_id, qtype, text)
    labels = {}
    for owner, oid, score in embeddings.neighbours(
        vec, qtype, ["question", "draft"], exclude=("draft", draft.pk)
    ):
        if owner == "question":
            labels[oid] = (
                Question.objects.filter(pk=oid).values_list("title", flat=True).first()
            )
        else:
            labels[oid] = (
                DraftQuestion.objects.filter(pk=oid)
                .values_list("title", flat=True)
                .first()
            )
        if labels[oid]:
            hit(owner, oid, labels[oid], "embedding", score)
    runs = dedup.runs(text, t["copy_run_words"])
    pages = SourcePage.objects.filter(document__exam=draft.job.exam).select_related(
        "document"
    )
    for page in pages:
        if (
            page.minhash
            and dedup.jaccard(page.minhash, draft.minhash) >= t["copy_minhash"]
        ):
            hits.append(
                SimilarityHit(
                    draft=draft,
                    target_type="source",
                    target_id=str(page.pk),
                    target_label=str(page)[:255],
                    method="minhash",
                    score=dedup.jaccard(page.minhash, draft.minhash),
                    verdict="copy_risk",
                )
            )
        shared = runs & dedup.runs(page.text, t["copy_run_words"])
        if shared:
            hit("source", page.pk, page, "run", float(len(shared)))
    draft.similar.all().delete()
    SimilarityHit.objects.bulk_create(hits)
    verdict = max((h.verdict for h in hits), key=dedup.SEVERITY.get, default="unique")
    draft.verdict = verdict
    draft.dedup = {
        "hits": len(hits),
        "embedding_model": embeddings.model_name(),
        "top": [
            {"label": h.target_label, "method": h.method, "score": h.score}
            for h in sorted(hits, key=lambda h: -h.score)[:5]
        ],
    }
    draft.save(update_fields=["verdict", "dedup", "updated_at"])
    with step("dedup", job=draft.job, draft=draft) as rec:
        rec.provider = embeddings.model_name()
        rec.output = {"verdict": verdict, **draft.dedup}


def plan_media(draft):
    """Only what the type needs: audio for scripts, chart / image / map."""
    s = draft.stimulus or {}
    pol = C.policy_for(draft.question_type)
    draft.media.filter(status=MediaRequest.Status.PENDING).delete()
    wanted = []
    script = s.get("script") or []
    contract = draft.contract
    if draft.question_type.engine == C.E.HIW:
        script = [{"speaker": "Narrator", "text": contract.get("spoken", "")}]
    elif draft.question_type.engine == C.E.DICTATION:
        script = [{"speaker": "Narrator", "text": contract.get("sentence", "")}]
    if script:
        wanted.append(("audio", Asset.Role.STIMULUS_AUDIO, {"turns": script}))
    if s.get("chart"):
        wanted.append(("chart", Asset.Role.STIMULUS_IMAGE, {"chart": s["chart"]}))
    if pol.get("stimulus") == "map" and s.get("map_labels"):
        spec = {"prompt": s.get("image_prompt", ""), "labels": s["map_labels"]}
        wanted.append(("map", Asset.Role.STIMULUS_IMAGE, spec))
    elif s.get("image_prompt") and pol.get("image"):
        wanted.append(
            ("image", Asset.Role.STIMULUS_IMAGE, {"prompt": s["image_prompt"]})
        )
    for kind, role, spec in wanted:
        if not draft.media.filter(kind=kind, status=MediaRequest.Status.DONE).exists():
            MediaRequest.objects.create(draft=draft, kind=kind, role=role, spec=spec)
    if draft.status != draft.Status.NEEDS_REVISION:
        draft.status = draft.Status.MEDIA_PENDING
        draft.save(update_fields=["status", "updated_at"])


def make_media(draft):
    for req in draft.media.exclude(status=MediaRequest.Status.DONE):
        req.attempts += 1
        try:
            with step(
                "media", job=draft.job, draft=draft, payload={"kind": req.kind}
            ) as rec:
                req.asset = _render(req)
                req.provider = req.asset.provider
                req.status, req.error = req.Status.DONE, ""
                rec.provider = f"{req.asset.provider}:{req.asset.model_name}"
                rec.output = {
                    "asset": str(req.asset.pk),
                    "file": req.asset.file.name,
                    "bytes": req.asset.file.size,
                    "duration_ms": req.asset.duration_ms,
                }
        except Exception as exc:
            req.status, req.error = req.Status.FAILED, str(exc)[:2000]
        req.save()
    pending = draft.media.exclude(status=MediaRequest.Status.DONE).exists()
    if draft.status == draft.Status.MEDIA_PENDING and not pending:
        draft.status = draft.Status.READY
        draft.save(update_fields=["status", "updated_at"])


def _render(req):
    draft = req.draft
    name = f"{draft.question_type.code.lower()}-{draft.pk}"
    if req.kind == "audio":
        data, ctype, ext, ms, provider, model, cast = tts.synthesize(req.spec["turns"])
        return save_asset(
            data,
            f"{name}.{ext}",
            kind=Asset.Kind.AUDIO,
            role=req.role,
            content_type=ctype,
            provider=provider,
            model_name=model,
            duration_ms=ms,
            prompt=" ".join(t["text"] for t in req.spec["turns"])[:5000],
            meta={"voices": cast, "draft": draft.pk},
        )
    if req.kind == "chart":
        data, w, h = charts.render(req.spec["chart"])
        provider, model, prompt = "matplotlib", "", json.dumps(req.spec["chart"])
    else:
        img, provider, model = images.generate(req.spec["prompt"])
        if req.kind == "map":
            img = images.label_map(img, req.spec["labels"])
        data, w, h = images.to_png(img)
        prompt = req.spec["prompt"]
    return save_asset(
        data,
        f"{name}.png",
        kind=Asset.Kind.IMAGE,
        role=req.role,
        content_type="image/png",
        provider=provider,
        model_name=model,
        width=w,
        height=h,
        prompt=prompt,
        meta={"draft": draft.pk, "mock": provider == "mock"},
    )


def revise(draft, feedback=""):
    """Re-write with reviewer / validator / admin feedback; old draft rejected."""
    problems = [i["message"] for i in draft.validation.get("issues", [])]
    problems += [
        f"Q{d['key']}: reviewer answered {d['reviewer']!r}, key {d['expected']!r}"
        for d in draft.review.get("disagreements", [])
    ]
    problems += draft.review.get("issues", [])
    if feedback or draft.admin_feedback:
        problems.append(f"Editor: {feedback or draft.admin_feedback}")
    brief = QuestionBrief(
        topic=draft.topic, subtopic=draft.subtopic, difficulty=draft.difficulty
    )
    new = write_draft(draft.job, brief, feedback=problems, revision_of=draft)
    draft.status = draft.Status.REJECTED
    draft.save(update_fields=["status", "updated_at"])
    process_draft(new)
    return new
