from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("institutes/", views.InstitutesView.as_view(), name="institutes"),
    path("contact/", views.ContactView.as_view(), name="contact"),
]
