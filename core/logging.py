"""
Custom logging utilities.
"""

import logging
from typing import Any, Dict
from django.utils import timezone

class ContextLogger:
    """
    Logger with context information.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
    
    def add_context(self, **kwargs):
        """Add context to logger."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear context."""
        self.context = {}
    
    def _log(self, level: int, message: str, **kwargs):
        """Log with context."""
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)


def log_request(request, response=None):
    """
    Log HTTP request and response.
    
    Args:
        request: Django request object
        response: Django response object (optional)
    """
    logger = logging.getLogger('apps.api')
    
    log_data = {
        'method': request.method,
        'path': request.path,
        'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
        'ip': get_client_ip(request),
        'timestamp': timezone.now().isoformat(),
    }
    
    if response:
        log_data['status_code'] = response.status_code
    
    logger.info(f"{request.method} {request.path}", extra=log_data)


def log_celery_task(task_name: str, task_id: str, status: str, **kwargs):
    """
    Log Celery task execution.
    
    Args:
        task_name: Name of the task
        task_id: Task ID
        status: Task status (started, success, failure)
        **kwargs: Additional context
    """
    logger = logging.getLogger('celery')
    
    log_data = {
        'task_name': task_name,
        'task_id': task_id,
        'status': status,
        'timestamp': timezone.now().isoformat(),
        **kwargs
    }
    
    logger.info(f"Task {task_name} [{status}]", extra=log_data)


def get_client_ip(request) -> str:
    """Get client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip