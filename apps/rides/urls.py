"""
URL configuration for rides app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.rides.views import RideViewSet

router = DefaultRouter()
router.register(r'', RideViewSet, basename='ride')

urlpatterns = [path('', include(router.urls))]