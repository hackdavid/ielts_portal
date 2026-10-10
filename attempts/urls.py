from django.urls import path

from . import views

app_name = "attempts"

urlpatterns = [
    path(
        "attempts/<uuid:pk>/mic-check/", views.MicCheckView.as_view(), name="mic_check"
    ),
    path("attempts/<uuid:pk>/play/", views.PlayView.as_view(), name="play"),
    path("attempts/<uuid:pk>/next-section/", views.next_section, name="next_section"),
    path("attempts/<uuid:pk>/submit/", views.submit, name="submit"),
    path("attempts/<uuid:pk>/submitted/", views.DoneView.as_view(), name="done"),
    path("attempts/<uuid:pk>/review/", views.ReviewView.as_view(), name="review"),
    path(
        "attempts/<uuid:pk>/items/<int:order>/recording/",
        views.recording,
        name="recording",
    ),
    path("api/attempts/<uuid:pk>/state/", views.api_state, name="state"),
    path(
        "api/attempts/<uuid:pk>/items/<int:order>/save/",
        views.api_save,
        name="autosave",
    ),
    path(
        "api/attempts/<uuid:pk>/items/<int:order>/play/",
        views.api_play,
        name="play_count",
    ),
    path(
        "api/attempts/<uuid:pk>/items/<int:order>/audio/", views.api_audio, name="audio"
    ),
]
