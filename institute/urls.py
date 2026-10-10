from django.urls import path

from . import views

app_name = "institute"

urlpatterns = [
    path("org/", views.ConsoleView.as_view(), name="console"),
]
