from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    return JsonResponse({"ok": True, "status": "ok", "time": timezone.now()})
