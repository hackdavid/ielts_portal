import json
import logging

from django.conf import settings
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import RedirectView, TemplateView, UpdateView

from .firebase import FirebaseAuthError, validate_claims, verify_id_token
from .forms import OnboardingForm
from .models import Role
from .permissions import RoleRequiredMixin
from .services import get_profile, home_url_for, sync_auth_context, user_from_claims

logger = logging.getLogger(__name__)


def _safe_next(request, url):
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return None


def _rate_limited(request):
    key = f"firebase-login:{request.META.get('REMOTE_ADDR', '')}"
    cache.add(key, 0, timeout=60)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=60)
        count = 1
    return count > settings.FIREBASE_LOGIN_RATE_LIMIT_PER_MINUTE


class LoginView(TemplateView):
    template_name = "accounts/login.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(home_url_for(request.user))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        emulator = settings.FIREBASE_AUTH_EMULATOR_HOST
        context["firebase_client_config"] = {
            "web": settings.FIREBASE_WEB_CONFIG,
            "emulatorUrl": f"http://{emulator}" if emulator else "",
            "next": _safe_next(self.request, self.request.GET.get("next")) or "",
        }
        context["firebase_configured"] = all(settings.FIREBASE_WEB_CONFIG.values())
        return context


class RegisterView(RedirectView):
    pattern_name = "accounts:login"
    query_string = True


class HomeRedirectView(RoleRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        return home_url_for(self.request.user, self.request.auth_context)


@require_POST
def firebase_login(request):
    if _rate_limited(request):
        return JsonResponse(
            {"error": "Too many sign-in attempts. Try again in a minute."}, status=429
        )
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        payload = None
    id_token = payload.get("id_token") if isinstance(payload, dict) else None
    if not isinstance(id_token, str) or not id_token:
        return JsonResponse({"error": "Missing id_token."}, status=400)
    try:
        claims = verify_id_token(id_token)
        email = validate_claims(claims)
        user = user_from_claims(claims, email)
    except FirebaseAuthError as exc:
        logger.warning("Firebase sign-in rejected: %s", exc)
        return JsonResponse({"error": str(exc)}, status=401)

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    context = sync_auth_context(request)
    target = home_url_for(user, context)
    if context["role"] == Role.STUDENT and get_profile(user).onboarded_at is not None:
        target = _safe_next(request, payload.get("next")) or target
    return JsonResponse({"ok": True, "redirect": target})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True, "redirect": reverse("pages:home")})


@require_GET
def me(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"authenticated": False})
    profile = get_profile(user)
    context = request.auth_context or sync_auth_context(request)
    return JsonResponse(
        {
            "authenticated": True,
            "org": context["tenant_name"],
            "email": user.email,
            "display_name": profile.display_name,
            "avatar_url": profile.avatar_url,
            "role": context["role"],
            "onboarded": profile.onboarded_at is not None,
            "home_url": home_url_for(user, context),
        }
    )


class OnboardingView(RoleRequiredMixin, UpdateView):
    template_name = "accounts/onboarding.html"
    form_class = OnboardingForm
    success_url = reverse_lazy("accounts:home")
    roles = (Role.STUDENT,)

    def get_object(self, queryset=None):
        return get_profile(self.request.user)

    def form_valid(self, form):
        form.instance.onboarded_at = form.instance.onboarded_at or timezone.now()
        return super().form_valid(form)
