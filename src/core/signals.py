from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Tạo UserProfile mỗi khi User mới được tạo"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Cập nhật UserProfile khi User được cập nhật"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # Nếu đã có User nhưng chưa có profile, tạo mới
        UserProfile.objects.create(user=instance) 