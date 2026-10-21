"""Images: Gemini ("Nano Banana") for scenes / map bases, Pillow for labels.

Without GEMINI_API_KEY a labelled MOCK placeholder is drawn instead.
"""

import base64
import io
import textwrap

import httpx
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def gemini_ready():
    return bool(settings.GEMINI_API_KEY)


def _font(size):
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _mock(prompt, size=(1024, 640)):
    img = Image.new("RGB", size, "#e2e8f0")
    draw = ImageDraw.Draw(img)
    draw.rectangle([8, 8, size[0] - 8, size[1] - 8], outline="#94a3b8", width=4)
    draw.text((32, 28), "MOCK IMAGE (no Gemini key)", fill="#b91c1c", font=_font(28))
    body = "\n".join(textwrap.wrap(prompt, 70)[:14])
    draw.multiline_text((32, 90), body, fill="#334155", font=_font(20), spacing=8)
    return img


def generate(prompt):
    """Prompt → (PIL image, provider, model)."""
    if not gemini_ready():
        return _mock(prompt), "mock", "mock-image"
    model = settings.GEMINI_IMAGE_MODEL
    resp = httpx.post(
        ENDPOINT.format(model=model),
        params={"key": settings.GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        },
        timeout=120,
    )
    resp.raise_for_status()
    for cand in resp.json().get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
            if data:
                img = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")
                return img, "gemini", model
    raise RuntimeError("Gemini returned no image.")


def label_map(img, labels):
    """Draw exact A–G letters in circles at fractional positions."""
    draw = ImageDraw.Draw(img)
    r = max(18, img.width // 40)
    font = _font(int(r * 1.2))
    for lab in labels:
        x, y = lab["x"] * img.width, lab["y"] * img.height
        draw.ellipse([x - r, y - r, x + r, y + r], fill="white", outline="black", width=3)
        draw.text((x, y), lab["letter"], fill="black", font=font, anchor="mm")
    return img


def to_png(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), img.width, img.height
