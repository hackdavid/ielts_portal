from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Role, UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        role = Role.SUPER_ADMIN if instance.is_superuser else Role.STUDENT
        UserProfile.objects.get_or_create(
            user=instance, defaults={"role_primary": role}
        )
