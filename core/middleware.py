"""
Custom middleware.
"""

import logging
import time
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

logger = logging.getLogger('apps.api')

class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all HTTP requests and responses.
    """
    
    def process_request(self, request):
        """Log request start."""
        request.start_time = time.time()
        
        # Don't log static files and admin
        if request.path.startswith('/static/') or request.path.startswith('/admin/'):
            return None
        
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
                'ip': self.get_client_ip(request),
            }
        )
        
        return None
    
    def process_response(self, request, response):
        """Log request completion."""
        # Don't log static files and admin
        if request.path.startswith('/static/') or request.path.startswith('/admin/'):
            return response
        
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            logger.info(
                f"Request completed: {request.method} {request.path} - {response.status_code}",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration': f"{duration:.3f}s",
                    'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
                    'ip': self.get_client_ip(request),
                }
            )
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions."""
        logger.error(
            f"Request exception: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'exception': str(exception),
                'exception_type': type(exception).__name__,
                'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
                'ip': self.get_client_ip(request),
            },
            exc_info=True
        )
        
        return None
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip