from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("exams/", views.ExamListView.as_view(), name="exam_list"),
    path("exams/<slug:slug>/", views.ExamDetailView.as_view(), name="exam_detail"),
    path(
        "exams/<slug:slug>/types/<str:code>/",
        views.QuestionTypeListView.as_view(),
        name="qtype_list",
    ),
    path(
        "exams/<slug:slug>/types/<str:code>/practice/",
        views.PracticeStartView.as_view(),
        name="practice_start",
    ),
    path("exams/<slug:slug>/mocks/", views.MockListView.as_view(), name="mock_list"),
    path("mocks/<int:pk>/", views.MockDetailView.as_view(), name="mock_detail"),
    path("mocks/<int:pk>/start/", views.StartMockView.as_view(), name="mock_start"),
]
