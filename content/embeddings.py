"""Text embeddings: OpenAI-compatible endpoint, or a labelled hashing mock."""

import hashlib

import numpy as np
from django.conf import settings

from .contracts import norm

MOCK_MODEL = "mock-hash-256"


def model_name():
    if settings.CONTENT_LLM_API_KEY and settings.CONTENT_EMBEDDING_MODEL:
        return settings.CONTENT_EMBEDDING_MODEL
    return MOCK_MODEL


def _mock(text, dim=256):
    vec = np.zeros(dim, dtype=np.float32)
    tokens = norm(text).split()
    for a, b in zip(tokens, tokens[1:] + [""], strict=True):
        for gram in (a, f"{a} {b}"):
            h = int.from_bytes(hashlib.md5(gram.encode()).digest()[:4], "big")
            vec[h % dim] += 1.0 if h & 1 << 31 else -1.0
    return vec


def embed(texts):
    """List of texts → list of float32 vectors, plus the model used."""
    model = model_name()
    if model == MOCK_MODEL:
        return [_mock(t) for t in texts], model
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.CONTENT_LLM_API_KEY,
        base_url=settings.CONTENT_LLM_BASE_URL or None,
    )
    try:
        resp = client.embeddings.create(model=model, input=[t[:8000] for t in texts])
    except Exception:  # endpoint without embeddings → fall back, labelled
        return [_mock(t) for t in texts], MOCK_MODEL
    return [np.asarray(d.embedding, dtype=np.float32) for d in resp.data], model


def store(owner_type, owner_id, exam_id, qtype, text):
    from .models import Embedding

    text_hash = hashlib.sha256(norm(text).encode()).hexdigest()
    existing = Embedding.objects.filter(
        owner_type=owner_type, owner_id=str(owner_id), text_hash=text_hash
    ).first()
    if existing:
        return np.frombuffer(existing.vector, dtype=np.float32)
    (vec,), model = embed([text])
    Embedding.objects.update_or_create(
        owner_type=owner_type,
        owner_id=str(owner_id),
        model=model,
        defaults={
            "exam_id": exam_id,
            "question_type": qtype,
            "dim": len(vec),
            "vector": vec.tobytes(),
            "text_hash": text_hash,
        },
    )
    return vec


def neighbours(vec, qtype, owner_types, exclude=None, limit=5):
    """Brute-force cosine within one question type (bank sizes stay small)."""
    from .models import Embedding

    rows = Embedding.objects.filter(
        question_type=qtype, owner_type__in=owner_types, dim=len(vec)
    )
    if exclude:
        rows = rows.exclude(owner_type=exclude[0], owner_id=str(exclude[1]))
    rows = list(rows.values_list("owner_type", "owner_id", "vector"))
    if not rows:
        return []
    mat = np.stack([np.frombuffer(r[2], dtype=np.float32) for r in rows])
    norms = np.linalg.norm(mat, axis=1) * (np.linalg.norm(vec) or 1.0)
    scores = mat @ vec / np.where(norms == 0, 1, norms)
    order = np.argsort(-scores)[:limit]
    return [(rows[i][0], rows[i][1], float(scores[i])) for i in order]
