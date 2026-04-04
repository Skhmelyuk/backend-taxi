from django.contrib import admin
from django.urls import path, include
from core.admin_site import taxi_admin
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from core.admin_site import taxi_admin

# Customize admin site
admin.site.site_header = 'Taxi Service Administration'
admin.site.site_title = 'Taxi Admin'
admin.site.index_title = 'Welcome to Taxi Service Admin Panel'

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': 'v1',
        'database': 'connected'
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_endpoint(request):
    """Protected endpoint for testing Clerk authentication."""
    return Response({
        'message': 'You are authenticated!',
        'user': {
            'id': str(request.user.id),
            'email': request.user.email,
            'full_name': request.user.full_name,
            'role': request.user.role,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_endpoint(request):
    """Protected endpoint for testing Clerk authentication."""
    return Response({
        'message': 'You are authenticated!',
        'user': {
            'id': str(request.user.id),
            'email': request.user.email,
            'full_name': request.user.full_name,
            'role': request.user.role,
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root endpoint."""
    return Response({
        'message': 'Taxi Service API',
        'version': 'v1',
        'endpoints': {
            'health': '/api/v1/health/',
            'protected': '/api/v1/protected/',
            'admin': '/admin/',
            'api-docs': '/api/v1/docs/',
        }
    })


urlpatterns = [
    path('admin/', taxi_admin.urls),
    path('api/v1/', api_root, name='api-root'),
    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/protected/', protected_endpoint, name='protected'),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/drivers/', include('apps.drivers.urls')),
    path('api/v1/rides/', include('apps.rides.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
]
