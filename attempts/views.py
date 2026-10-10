import json
import time

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from accounts.permissions import RoleRequiredMixin
from catalog.models import Asset
from scoring import presentation
from scoring.models import ScoreBreakdown

from . import services
from .models import Attempt
from .rendering import build

MAX_AUDIO_BYTES = 10 * 1024 * 1024
AUDIO_TYPES = ("audio/", "video/webm")


def _own(request, pk):
    return get_object_or_404(
        Attempt.objects.select_related("exam", "pack"), pk=pk, user=request.user
    )


def _ms(dt):
    return int(dt.timestamp() * 1000) if dt else None


def _clock(attempt):
    section = services.current_section(attempt)
    return {
        "status": attempt.status,
        "section_index": services.section_index(attempt),
        "section": section["section"] if section else None,
        "deadline_ms": _ms(attempt.server_deadline_at),
        "server_now_ms": int(time.time() * 1000),
        "grace_sec": services.GRACE_SEC,
    }


class AttemptMixin(RoleRequiredMixin):
    def get_attempt(self):
        return services.sync_clock(_own(self.request, self.kwargs["pk"]))


class MicCheckView(AttemptMixin, TemplateView):
    template_name = "attempts/mic_check.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "attempt": self.get_attempt()}

    def post(self, request, *args, **kwargs):
        attempt = self.get_attempt()
        attempt.meta["mic_checked"] = request.POST.get("result", "ok")
        attempt.save(update_fields=["meta", "updated_at"])
        return redirect("attempts:play", attempt.pk)


class PlayView(AttemptMixin, TemplateView):
    template_name = "attempts/play.html"

    def get(self, request, *args, **kwargs):
        attempt = self.get_attempt()
        if attempt.status != Attempt.Status.IN_PROGRESS:
            return redirect("attempts:done", attempt.pk)
        if services.needs_mic_check(attempt):
            return redirect("attempts:mic_check", attempt.pk)
        items = [build(i) for i in services.current_items(attempt)]
        rows = services.sections(attempt)
        index = services.section_index(attempt)
        context = self.get_context_data(
            attempt=attempt,
            items=items,
            section=rows[index],
            sections=rows,
            section_index=index,
            is_last=index == len(rows) - 1,
            clock=_clock(attempt),
            listening=attempt.config_snapshot.get("listening", {}),
            reading_split=rows[index]["section"] == "reading"
            and any(i["passage"] for i in items),
        )
        return self.render_to_response(context)


@login_required
@require_POST
def next_section(request, pk):
    attempt = services.sync_clock(_own(request, pk))
    if attempt.status == Attempt.Status.IN_PROGRESS:
        expected = request.POST.get("section_index")
        if expected is None or int(expected) == services.section_index(attempt):
            services.advance(attempt)
    if attempt.status == Attempt.Status.IN_PROGRESS:
        return redirect("attempts:play", attempt.pk)
    return redirect("attempts:done", attempt.pk)


@login_required
@require_POST
def submit(request, pk):
    services.finalize(_own(request, pk))
    return redirect("attempts:done", pk)


class DoneView(AttemptMixin, TemplateView):
    template_name = "attempts/submitted.html"

    def get(self, request, *args, **kwargs):
        attempt = self.get_attempt()
        if attempt.status == Attempt.Status.IN_PROGRESS:
            return redirect("attempts:play", attempt.pk)
        items = attempt.items.all()
        answered = sum(
            1 for i in items if i.audio_id or services.has_answer(i.response)
        )
        breakdown = None
        if attempt.status == Attempt.Status.SCORED:
            breakdown = ScoreBreakdown.objects.filter(attempt=attempt).first()
        context = self.get_context_data(
            attempt=attempt, total=len(items), answered=answered, breakdown=breakdown
        )
        if breakdown:
            context.update(
                overall=presentation.overall_text(breakdown),
                section_rows=presentation.section_rows(breakdown),
                trait_rows=presentation.trait_rows(breakdown),
            )
        return self.render_to_response(context)


class ReviewView(AttemptMixin, TemplateView):
    template_name = "attempts/review.html"

    def get(self, request, *args, **kwargs):
        attempt = self.get_attempt()
        if attempt.status != Attempt.Status.SCORED:
            return redirect("attempts:done", attempt.pk)
        return self.render_to_response(
            self.get_context_data(
                attempt=attempt, items=presentation.review_items(attempt)
            )
        )


# ---- JSON API (called through static/js/api.js) ----


def _api_item(request, pk, order):
    """Return (item, error JsonResponse | None)."""
    if not request.user.is_authenticated:
        return None, JsonResponse({"error": "Not signed in."}, status=401)
    attempt = Attempt.objects.filter(pk=pk, user=request.user).first()
    if attempt is None:
        return None, JsonResponse({"error": "Not found."}, status=404)
    services.sync_clock(attempt)
    item = attempt.items.filter(order=order).first()
    if item is None:
        return None, JsonResponse({"error": "Not found."}, status=404)
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return None, JsonResponse(
            {"error": "This attempt is already submitted.", "code": "submitted"},
            status=409,
        )
    section = services.current_section(attempt)
    if item.section_code != section["section"]:
        return None, JsonResponse(
            {"error": "This section is closed.", "code": "section_closed"}, status=409
        )
    return item, None


@require_POST
def api_save(request, pk, order):
    item, error = _api_item(request, pk, order)
    if error:
        return error
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    response = body.get("response")
    if not isinstance(response, dict) or len(request.body) > 200_000:
        return JsonResponse({"error": "Invalid response."}, status=400)
    now = timezone.now()
    item.response = response
    item.started_at = item.started_at or now
    item.save(update_fields=["response", "started_at", "updated_at"])
    return JsonResponse({"ok": True, "saved_at": now.isoformat()})


@require_POST
def api_play(request, pk, order):
    item, error = _api_item(request, pk, order)
    if error:
        return error
    limit = item.attempt.config_snapshot.get("listening", {}).get("max_plays", 0)
    count = int(item.response_flags.get("play_count", 0))
    if limit and count >= limit:
        return JsonResponse(
            {"error": "No plays left.", "code": "play_limit", "play_count": count},
            status=409,
        )
    item.response_flags["play_count"] = count + 1
    item.save(update_fields=["response_flags", "updated_at"])
    return JsonResponse({"ok": True, "play_count": count + 1, "max_plays": limit})


@require_POST
def api_audio(request, pk, order):
    item, error = _api_item(request, pk, order)
    if error:
        return error
    upload = request.FILES.get("audio")
    if upload is None or upload.size == 0:
        return JsonResponse({"error": "Empty recording."}, status=400)
    if upload.size > MAX_AUDIO_BYTES:
        return JsonResponse({"error": "Recording is too long."}, status=400)
    content_type = (upload.content_type or "").split(";")[0]
    if not content_type.startswith(AUDIO_TYPES):
        return JsonResponse({"error": "Unsupported audio format."}, status=415)
    ext = {
        "audio/ogg": "ogg",
        "audio/mp4": "m4a",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
    }
    name = f"{item.attempt_id}-{item.order}.{ext.get(content_type, 'webm')}"
    asset = Asset(
        kind=Asset.Kind.AUDIO,
        tenant=item.attempt.tenant,
        content_type=content_type,
        meta={"attempt": str(item.attempt_id), "order": item.order, "private": True},
    )
    asset.file.save(f"recordings/{name}", ContentFile(upload.read()), save=False)
    asset.save()
    item.audio = asset
    item.response = {**(item.response or {}), "recorded": True}
    item.started_at = item.started_at or timezone.now()
    item.save(update_fields=["audio", "response", "started_at", "updated_at"])
    url = reverse("attempts:recording", args=[item.attempt_id, item.order])
    return JsonResponse({"ok": True, "asset_id": str(asset.pk), "url": url})


@require_GET
def api_state(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not signed in."}, status=401)
    attempt = Attempt.objects.filter(pk=pk, user=request.user).first()
    if attempt is None:
        return JsonResponse({"error": "Not found."}, status=404)
    return JsonResponse(_clock(services.sync_clock(attempt)))


@login_required
@require_GET
def recording(request, pk, order):
    item = get_object_or_404(
        _own(request, pk).items.select_related("audio"), order=order
    )
    if not item.audio_id:
        raise Http404
    return FileResponse(
        item.audio.file.open("rb"), content_type=item.audio.content_type
    )
