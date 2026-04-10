"""
Users app configuration.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration for users app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = '👥 Користувачі'

    def ready(self):
        """Import signals when app is ready."""
        # Import signals here if needed
        # import apps.users.signals
        pass
