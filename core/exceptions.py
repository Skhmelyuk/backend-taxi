import logging
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Handle exceptions raised by Django REST Framework and return standardized response.
    This handler wraps DRF and Django exceptions into a unified response format:

    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Error message",
            "details": {},
            "timestamp": "ISO_DATE"
        }
    }

    Also logs error details including status code, request, and view for debugging.
    Args:
        exc (Exception): The exception instance raised during request processing.
        context (dict): Context information containing request, view, and other metadata.

    Returns:
        Response | None: Standardized DRF Response object if exception handled,
        otherwise None to allow default handling.
    """

    response = exception_handler(exc, context)

    # Handle Django ValidationError manually
    if response is None and isinstance(exc, DjangoValidationError):
        response = Response(status=status.HTTP_400_BAD_REQUEST)

    if response is not None:
        error_code = exc.__class__.__name__
        error_message = str(exc)
        error_details = {}

        if isinstance(exc, DRFValidationError):
            if isinstance(response.data, dict):
                error_details = response.data
            else:
                error_details = {"detail": response.data}

        elif hasattr(exc, "detail"):
            if isinstance(exc.detail, dict):
                error_details = exc.detail
            else:
                error_details = {"detail": str(exc.detail)}

        response.data = {
            "error": {
                "code": error_code,
                "message": error_message,
                "details": error_details,
                "timestamp": timezone.now().isoformat(),
            }
        }

        logger.error(
            f"API Error: {error_code} - {error_message}",
            extra={
                "status_code": response.status_code,
                "details": error_details,
                "view": str(context.get("view")),
                "request": context.get("request"),
            },
        )

    return response


class APIException(Exception):
    """
    Base class for all custom API exceptions.
    Provides standardized attributes:
    - HTTP status code
    - error code
    - human-readable error message
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = "error"
    default_message = "An error occurred"

    def __init__(self, message=None, code=None, status_code=None):
        """
        Initialize APIException.
        Args:
            message (str, optional): Custom error message.
            code (str, optional): Custom error code.
            status_code (int, optional): Custom HTTP status code.
        """
        self.message = message or self.default_message
        self.code = code or self.default_code

        if status_code:
            self.status_code = status_code

    def __str__(self):
        """
        Return string representation of exception.
        Returns:
            str: Error message.
        """
        return self.message


class ValidationException(APIException):
    """
    Exception raised when validation fails.
    Returns HTTP 400 Bad Request response.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"
    default_message = "Validation failed"


class AuthenticationException(APIException):
    """
    Exception raised when authentication fails.
    Returns HTTP 401 Unauthorized response.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "authentication_failed"
    default_message = "Authentication failed"


class PermissionException(APIException):
    """
    Exception raised when user lacks required permissions.
    Returns HTTP 403 Forbidden response.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_denied"
    default_message = "Permission denied"


class NotFoundException(APIException):
    """
    Exception raised when requested resource is not found.
    Returns HTTP 404 Not Found response.
    """
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
    default_message = "Resource not found"