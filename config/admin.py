"""
Django Admin customization.
"""

from django.contrib import admin
from django.contrib.admin import AdminSite

class TaxiAdminSite(AdminSite):
    """Custom admin site."""
    
    site_header = 'Taxi Service Administration'
    site_title = 'Taxi Admin'
    index_title = 'Welcome to Taxi Service Admin Panel'

# Create custom admin site instance
admin_site = TaxiAdminSite(name='admin')