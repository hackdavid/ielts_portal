from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("accounts/login/", views.LoginView.as_view(), name="login"),
    path("accounts/register/", views.RegisterView.as_view(), name="register"),
    path("accounts/home/", views.HomeRedirectView.as_view(), name="home"),
    path("onboarding/", views.OnboardingView.as_view(), name="onboarding"),
    path("api/auth/firebase/", views.firebase_login, name="firebase_login"),
    path("api/auth/logout/", views.logout_view, name="logout"),
    path("api/auth/me/", views.me, name="me"),
]
