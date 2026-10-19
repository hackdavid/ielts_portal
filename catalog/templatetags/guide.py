from django import template
from django.utils.html import format_html_join

from catalog import guide

register = template.Library()


@register.filter
def qtype_guide(code):
    return guide.qtype_guide(code)


@register.simple_tag
def section_guide(code, kind="ielts"):
    return guide.section_guide(code, kind)


@register.simple_tag
def exam_guide(exam):
    return guide.exam_guide(exam)


@register.filter
def minutes(seconds):
    try:
        return round(int(seconds) / 60)
    except (TypeError, ValueError):
        return 0


@register.filter
def paragraphs(text):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return format_html_join(
        "", '<p class="mb-4 last:mb-0">{}</p>', ((line,) for line in lines)
    )
