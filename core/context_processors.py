from django.conf import settings


def site(request):
    return {"PRACTICE_SCORE_DISCLAIMER": settings.PRACTICE_SCORE_DISCLAIMER}
