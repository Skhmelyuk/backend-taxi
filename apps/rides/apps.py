"""
Rides app configuration.
"""

from django.apps import AppConfig


class RidesConfig(AppConfig):
    """Configuration for rides app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rides'
    verbose_name = 'Rides'
