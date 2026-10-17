from django import template

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
