"""Duplicate detection, cheapest first: exact hash → MinHash → embeddings.

Plus a copy guard against uploaded source pages (generated text must be original).
"""

import hashlib
import re

import numpy as np
from django.conf import settings

from catalog.models import Question

from .contracts import norm

PERMS = 128
_rng = np.random.default_rng(20261015)
_XOR = _rng.integers(1, 2**63, size=PERMS, dtype=np.uint64)
_MUL = _rng.integers(1, 2**63, size=PERMS, dtype=np.uint64) | np.uint64(1)
MAX64 = np.iinfo(np.uint64).max


def content_hash(type_code, text):
    return hashlib.sha256(f"{type_code}\n{norm(text)}".encode()).hexdigest()


def shingles(text):
    tokens = norm(text).split()
    if len(tokens) >= 20:
        return {" ".join(tokens[i : i + 3]) for i in range(len(tokens) - 2)}
    flat = " ".join(tokens)
    return {flat[i : i + 5] for i in range(max(len(flat) - 4, 1))}


def _h64(s):
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big")


def minhash(text):
    grams = shingles(text)
    if not grams:
        return np.full(PERMS, MAX64, dtype=np.uint64).tobytes()
    base = np.fromiter((_h64(g) for g in grams), dtype=np.uint64, count=len(grams))
    with np.errstate(over="ignore"):
        x = (base[:, None] ^ _XOR[None, :]) * _MUL[None, :]
        x ^= x >> np.uint64(29)
    return x.min(axis=0).astype(np.uint64).tobytes()


def jaccard(a, b):
    if not a or not b:
        return 0.0
    va = np.frombuffer(bytes(a), dtype=np.uint64)
    vb = np.frombuffer(bytes(b), dtype=np.uint64)
    if va.shape != vb.shape:
        return 0.0
    return float((va == vb).mean())


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


def runs(text, n):
    tokens = norm(text).split()
    return {_h64(" ".join(tokens[i : i + n])) for i in range(len(tokens) - n + 1)}


def question_text(question):
    """Student-visible text of an existing question (stem + stimulus)."""
    stem = question.stem or {}
    parts = [(question.scorer_meta or {}).get("transcript", "")]
    if question.stimulus_id:
        parts += [question.stimulus.body]
    for key in ("passage", "prompt", "text", "transcript", "context"):
        if isinstance(stem.get(key), str):
            parts.append(stem[key])
    for key in ("items", "statements", "paragraphs", "options"):
        for row in stem.get(key) or []:
            parts.append(row.get("text", "") if isinstance(row, dict) else str(row))
    parts += [q for q in stem.get("questions") or [] if isinstance(q, str)]
    cue = stem.get("cue_card")
    if isinstance(cue, dict):
        parts += [cue.get("topic", ""), *cue.get("points", [])]
    parts.append((question.answer_key or {}).get("sentence", ""))
    return "\n".join(p for p in parts if p)


def index_question(question, embed=True):
    """Fill content_hash / minhash (and the embedding) for a bank question."""
    text = question_text(question)
    question.content_hash = content_hash(question.question_type.code, text)
    question.minhash = minhash(text)
    Question.objects.filter(pk=question.pk).update(
        content_hash=question.content_hash, minhash=question.minhash
    )
    if embed:
        from .embeddings import store

        store("question", question.pk, question.exam_id, question.question_type, text)
    return text


def verdict_for(method, score):
    t = settings.CONTENT_DEDUP
    if method == "exact":
        return "duplicate"
    if method == "minhash":
        if score >= t["minhash_duplicate"]:
            return "duplicate"
        return "similar" if score >= t["minhash_similar"] else None
    if method == "embedding":
        if score >= t["embedding_duplicate"]:
            return "duplicate"
        return "similar" if score >= t["embedding_similar"] else None
    return "copy_risk"


SEVERITY = {"unique": 0, "similar": 1, "duplicate": 2, "copy_risk": 3}
STRIP = re.compile(r"\s+")
