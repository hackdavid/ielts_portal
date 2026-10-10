from django.urls import path

from . import views

app_name = "institute"

urlpatterns = [
    path("org/", views.ConsoleView.as_view(), name="console"),
    path("org/students/", views.StudentsView.as_view(), name="students"),
    path(
        "org/students/<int:user_id>/",
        views.StudentDetailView.as_view(),
        name="student_detail",
    ),
    path("org/access/", views.AccessView.as_view(), name="access"),
]
