from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from tenancy.models import AccessInvite

from .models import Role, User, UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        role = Role.SUPER_ADMIN if instance.is_superuser else Role.STUDENT
        UserProfile.objects.get_or_create(
            user=instance, defaults={"role_primary": role}
        )


@receiver(post_save, sender=AccessInvite)
def apply_invite_to_existing_user(sender, instance, raw=False, **kwargs):
    if raw or not instance.is_active:
        return
    from .services import apply_invitations

    user = User.objects.filter(email__iexact=instance.email, is_active=True).first()
    if user is not None:
        apply_invitations(user)
