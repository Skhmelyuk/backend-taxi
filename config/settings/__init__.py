"""
Settings module initialization.
Automatically loads the correct settings based on DJANGO_SETTINGS_MODULE.
"""

import os

# Default to development settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')