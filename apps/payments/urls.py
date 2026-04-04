"""
URL configuration for payments app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.payments.views import PaymentViewSet, fondy_callback, liqpay_callback

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment')

urlpatterns = [
    path('callback/liqpay/', liqpay_callback, name='liqpay-callback'),
    path('callback/fondy/', fondy_callback, name='fondy-callback'),
    path('', include(router.urls)),
]
