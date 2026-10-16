"""Store generated / uploaded files as catalog Assets (R2 or local disk)."""

import hashlib

from django.core.files.base import ContentFile

from catalog.models import Asset


def save_asset(data, filename, *, kind, role, content_type, provider, **fields):
    """Reuse an existing Asset with the same bytes, else upload a new one."""
    sha = hashlib.sha256(data).hexdigest()
    existing = Asset.objects.filter(sha256=sha).first()
    if existing:
        return existing
    asset = Asset(
        kind=kind,
        role=role,
        content_type=content_type,
        provider=provider,
        sha256=sha,
        **fields,
    )
    asset.file.save(f"generated/{sha[:2]}/{sha[:16]}-{filename}", ContentFile(data))
    return asset
