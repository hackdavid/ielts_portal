"""Turn a stem snapshot + saved response into a template-friendly view model.

Only stem data is used; answer keys and transcripts never reach this module.
"""

import re

from catalog.models import Asset, QuestionType

E = QuestionType.Engine
LETTER = re.compile(r"^([A-Z]|[ivx]+)$")
BLANK = re.compile(r"\{(\w+)\}")


def _option(raw):
    if isinstance(raw, dict):
        return {"value": str(raw["id"]), "label": raw.get("text", raw["id"])}
    raw = str(raw)
    head, _, rest = raw.partition(" ")
    if rest and LETTER.match(head):
        return {"value": head, "label": raw}
    return {"value": raw, "label": raw}


def _question(key, label, text, options, saved, multi=False, word_limit=None):
    value = saved.get(key, [] if multi else "")
    opts = [_option(o) for o in options or []]
    for o in opts:
        o["checked"] = o["value"] in value if multi else o["value"] == value
    if not opts:
        kind = "text"
    elif multi:
        kind = "checkbox"
    elif len(opts) > 5:
        kind = "select"
    else:
        kind = "radio"
    return {
        "key": key,
        "label": label,
        "text": text,
        "kind": kind,
        "options": opts,
        "value": value,
        "word_limit": word_limit,
    }


def _inline(text, blanks, saved, bank=None):
    """Split '{1}'-style templates into text / blank parts."""
    by_id = {str(b["id"]): b for b in blanks or []}
    parts = []
    for i, chunk in enumerate(BLANK.split(text or "")):
        if i % 2 == 0:
            if chunk:
                parts.append({"text": chunk})
            continue
        options = (by_id.get(chunk) or {}).get("options") or bank
        parts.append(
            {
                "blank": _question(chunk, chunk, "", options, saved),
            }
        )
    return parts


def asset_url(asset_id):
    if not asset_id:
        return None
    asset = Asset.objects.filter(pk=asset_id).only("file").first()
    return asset.file.url if asset and asset.file else None


def build(item):
    stem = item.stem_snapshot or {}
    saved = item.response or {}
    engine = stem.get("_engine", "")
    view = {
        "order": item.order,
        "engine": engine,
        "qtype": stem.get("_qtype", ""),
        "part": stem.get("_part"),
        "audio": asset_url(stem.get("_audio_asset")) or stem.get("_audio"),
        "image": asset_url(stem.get("_image_asset")),
        "passage": stem.get("passage"),
        "instructions": stem.get("instructions"),
        "context": stem.get("context"),
        "prompt": stem.get("prompt"),
        "data_table": stem.get("data_table"),
        "kind": "questions",
        "questions": [],
    }
    if engine == E.WRITING_TEXT:
        view.update(
            kind="writing",
            text=saved.get("text", ""),
            min_words=stem.get("min_words"),
            max_words=stem.get("max_words"),
        )
    elif engine == E.SPEAKING_AUDIO:
        view.update(
            kind="speaking",
            questions_list=stem.get("questions") or [],
            cue_card=stem.get("cue_card"),
            prep_sec=stem.get("prep_sec") or 0,
            record_sec=stem.get("talk_sec") or stem.get("record_sec") or 120,
            has_recording=bool(item.audio_id),
        )
    elif engine == E.REORDER:
        paras = {p["id"]: p for p in stem.get("paragraphs", [])}
        order = [i for i in saved.get("order", []) if i in paras]
        order += [i for i in paras if i not in order]
        view.update(kind="reorder", paragraphs=[paras[i] for i in order])
    elif engine == E.HIW:
        chosen = {str(i) for i in saved.get("selected", [])}
        words = (stem.get("transcript") or "").split()
        view.update(
            kind="hiw",
            words=[
                {"i": str(i), "w": w, "checked": str(i) in chosen}
                for i, w in enumerate(words)
            ],
        )
    elif engine == E.DICTATION:
        view["questions"] = [_question("answer", "", "", None, saved)]
    elif stem.get("items"):
        limit = stem.get("word_limit")
        view["questions"] = [
            _question(
                str(it.get("n", it.get("id"))),
                str(it.get("n", it.get("id"))),
                it.get("text", ""),
                it.get("options") or stem.get("options"),
                saved,
                word_limit=limit,
            )
            for it in stem["items"]
        ]
    elif stem.get("statements"):
        view["questions"] = [
            _question(str(s["id"]), str(s["id"]), s["text"], stem.get("choices"), saved)
            for s in stem["statements"]
        ]
    elif "{" in (stem.get("text") or ""):
        view.update(
            kind="inline",
            parts=_inline(stem["text"], stem.get("blanks"), saved, stem.get("bank")),
            word_limit=stem.get("word_limit"),
        )
    elif stem.get("options"):
        multi = engine == E.MCQ_MULTI
        view["questions"] = [
            _question("answer", "", "", stem["options"], saved, multi=multi)
        ]
    return view
