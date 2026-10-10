from django.urls import path

from . import views

app_name = "plans"

urlpatterns = [
    path("locked/", views.LockedView.as_view(), name="locked"),
]
