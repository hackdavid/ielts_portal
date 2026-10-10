from django.db import transaction
from django.urls import reverse

from tenancy.models import Membership

from .firebase import FirebaseAuthError
from .models import Role, User, UserProfile


def get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@transaction.atomic
def user_from_claims(claims, email):
    """Find the user for a verified Google identity, linking or creating as needed."""
    uid = claims["uid"]
    user = User.objects.select_for_update().filter(firebase_uid=uid).first()
    if user is None:
        existing = User.objects.select_for_update().filter(email__iexact=email).first()
        if existing is not None and existing.firebase_uid:
            raise FirebaseAuthError("This email is linked to a different account.")
        if existing is not None:
            user = existing
            user.firebase_uid = uid
            user.save(update_fields=["firebase_uid"])
        else:
            user = User(username=uid[:150], email=email, firebase_uid=uid)
            user.set_unusable_password()
            user.save()
    if not user.is_active:
        raise FirebaseAuthError("This account is disabled.")

    profile = get_profile(user)
    updates = []
    if not profile.display_name and claims.get("name"):
        profile.display_name = claims["name"][:150]
        updates.append("display_name")
    picture = claims.get("picture") or ""
    if picture and picture != profile.avatar_url:
        profile.avatar_url = picture[:500]
        updates.append("avatar_url")
    if updates:
        profile.save(update_fields=[*updates, "updated_at"])
    return user


def is_super_admin(user):
    return user.is_authenticated and (
        user.is_superuser or get_profile(user).role_primary == Role.SUPER_ADMIN
    )


def is_institute_admin(user):
    if not user.is_authenticated:
        return False
    if get_profile(user).role_primary == Role.INSTITUTE_ADMIN:
        return True
    return Membership.objects.filter(
        user=user, is_active=True, role=Membership.Role.INSTITUTE_ADMIN
    ).exists()


def home_url_for(user):
    """Role-aware landing page after sign-in."""
    if is_super_admin(user):
        return reverse("accounts:platform")
    if is_institute_admin(user):
        return reverse("institute:console")
    if get_profile(user).onboarded_at is None:
        return reverse("accounts:onboarding")
    return reverse("analytics:dashboard")
