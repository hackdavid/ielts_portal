from django.conf import settings
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.static import serve


@require_GET
def health(request):
    return JsonResponse({"ok": True, "status": "ok", "time": timezone.now()})


PRIVATE_MEDIA_DIRS = ("recordings",)


def dev_media(request, path):
    """DEBUG-only media serving that never exposes private uploads (speaking
    recordings are served by attempts:recording with an ownership check)."""
    if any(part in PRIVATE_MEDIA_DIRS for part in path.split("/")):
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)
