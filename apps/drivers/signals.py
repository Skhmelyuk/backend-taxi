from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

@receiver(post_save, sender='drivers.Driver')
def sync_driver_to_user(sender, instance, **kwargs):
    """Sync names from Driver to User model."""
    user = instance.user
    if not user:
        return
        
    updated = False
    if instance.first_name and user.first_name != instance.first_name:
        user.first_name = instance.first_name
        updated = True
    if instance.last_name and user.last_name != instance.last_name:
        user.last_name = instance.last_name
        updated = True
        
    if updated:
        # We use update_fields to avoid triggering other signals if possible 
        # and to be explicit about what changed.
        user.save(update_fields=['first_name', 'last_name'])

@receiver(post_save, sender='users.User')
def sync_user_to_driver(sender, instance, **kwargs):
    """Sync names from User to Driver model."""
    # Check if user has a driver profile using the related_name 'driver_profile'
    if not hasattr(instance, 'driver_profile'):
        return
        
    driver = instance.driver_profile
    updated = False
    if instance.first_name and driver.first_name != instance.first_name:
        driver.first_name = instance.first_name
        updated = True
    if instance.last_name and driver.last_name != instance.last_name:
        driver.last_name = instance.last_name
        updated = True
        
    if updated:
        driver.save(update_fields=['first_name', 'last_name'])
