from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from tenancy.models import AccessInvite, Membership

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
    apply_invitations(user)

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


def apply_invitations(user):
    """Turn active access emails for this user into memberships."""
    if not user.email:
        return
    now = timezone.now()
    invites = AccessInvite.objects.filter(email__iexact=user.email, is_active=True)
    for invite in invites.select_related("tenant"):
        Membership.objects.update_or_create(
            tenant=invite.tenant,
            user=user,
            defaults={"role": invite.role, "is_active": True, "joined_at": now},
        )
        if invite.accepted_by_id is None:
            invite.accepted_by, invite.accepted_at = user, now
            invite.save(update_fields=["accepted_by", "accepted_at", "updated_at"])


def resolve_auth_context(user):
    """Role + org for a signed-in user, always computed from the database."""
    if user.is_superuser:
        return {"role": Role.SUPER_ADMIN, "tenant_id": None, "tenant_name": ""}
    memberships = (
        Membership.objects.filter(user=user, is_active=True, tenant__is_active=True)
        .select_related("tenant")
        .order_by("-role", "created_at")  # "student" sorts after "org"
    )
    membership = memberships.first()
    if membership is None:
        return {"role": Role.STUDENT, "tenant_id": None, "tenant_name": ""}
    role = Role.ORG if membership.role == Membership.Role.ORG else Role.STUDENT
    return {
        "role": role,
        "tenant_id": membership.tenant_id,
        "tenant_name": membership.tenant.name,
    }


def sync_auth_context(request):
    """Refresh role/org in the session and keep UserProfile.role_primary in step."""
    context = resolve_auth_context(request.user)
    if request.session.get("auth_context") != context:
        request.session["auth_context"] = context
        profile = get_profile(request.user)
        if profile.role_primary != context["role"]:
            profile.role_primary = context["role"]
            profile.save(update_fields=["role_primary", "updated_at"])
    request.auth_context = context
    return context


def home_url_for(user, context=None):
    """Role-aware landing page after sign-in."""
    context = context or resolve_auth_context(user)
    if context["role"] == Role.SUPER_ADMIN:
        return reverse("admin:index")
    if context["role"] == Role.ORG:
        return reverse("institute:console")
    if get_profile(user).onboarded_at is None:
        return reverse("accounts:onboarding")
    return reverse("analytics:dashboard")
