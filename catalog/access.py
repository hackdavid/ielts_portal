from django.db.models import Q
from django.utils import timezone

from plans.models import Entitlement


def tenant_id_for(request):
    return (getattr(request, "auth_context", None) or {}).get("tenant_id")


def visible(queryset, request):
    """Active global content plus content owned by the user's org."""
    tenant_id = tenant_id_for(request)
    scope = Q(tenant__isnull=True)
    if tenant_id:
        scope |= Q(tenant_id=tenant_id)
    return queryset.filter(scope, is_active=True)


def entitlement_keys(request):
    owner = Q(user=request.user)
    tenant_id = tenant_id_for(request)
    if tenant_id:
        owner |= Q(tenant_id=tenant_id)
    live = Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    return set(Entitlement.objects.filter(owner, live).values_list("key", flat=True))


def mark_locked(request, packs):
    """Set `pack.locked` on each pack; returns the list."""
    packs = list(packs)
    keys = entitlement_keys(request)
    unlimited = request.user.is_superuser or "unlimited" in keys
    for pack in packs:
        pack.locked = not (unlimited or pack.is_free or f"pack:{pack.pk}" in keys)
    return packs
