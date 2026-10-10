from django.utils.cache import patch_cache_control

from .services import sync_auth_context


class AuthContextMiddleware:
    """Re-check the signed-in user's role/org against the DB on every request.

    Inactive users are already dropped by ModelBackend.get_user. Pages for
    signed-in users are never cached so Back after logout can't show them.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.auth_context = None
        if request.user.is_authenticated:
            sync_auth_context(request)
        elif "auth_context" in request.session:
            del request.session["auth_context"]
        response = self.get_response(request)
        if request.user.is_authenticated:
            patch_cache_control(
                response,
                private=True,
                no_cache=True,
                no_store=True,
                must_revalidate=True,
            )
        return response
