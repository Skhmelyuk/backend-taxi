"""
Drivers app configuration.
"""

from django.apps import AppConfig


class DriversConfig(AppConfig):
    """Configuration for drivers app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.drivers'
    verbose_name = 'Drivers'

    def ready(self):
        """Import signals when app is ready."""
        import apps.drivers.signals  # noqa
