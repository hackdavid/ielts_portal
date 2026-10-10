"""URL configuration for the IELTS Portal project."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from core.views import dev_media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("", include("accounts.urls")),
    path("", include("analytics.urls")),
    path("", include("institute.urls")),
    path("", include("catalog.urls")),
    path("", include("attempts.urls")),
    path("", include("plans.urls")),
    path("", include("pages.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(rf"^{settings.MEDIA_URL.strip('/')}/(?P<path>.*)$", dev_media)
    ]
