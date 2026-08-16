from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, Role


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile for every Django user.

    Superusers/staff users receive the ADMIN CRM role.
    Regular users receive the STUDENT role by default.
    """

    if created:
        role = Role.ADMIN if instance.is_superuser else Role.STUDENT

        UserProfile.objects.create(
            user=instance,
            role=role,
        )


@receiver(post_save, sender=User)
def update_admin_profile(sender, instance, **kwargs):
    """
    Keep the CRM role synchronized for Django superusers.
    """

    if not hasattr(instance, "profile"):
        return

    if instance.is_superuser and instance.profile.role != Role.ADMIN:
        instance.profile.role = Role.ADMIN
        instance.profile.save(update_fields=["role"])