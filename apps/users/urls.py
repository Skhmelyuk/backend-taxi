"""
URL configuration for users app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import UserViewSet, clerk_webhook

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('webhooks/clerk/', clerk_webhook, name='clerk-webhook'),
    path('', include(router.urls)),
]
