import os
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value: str) -> None:
    """
    Validate international phone number format.
    Ensures phone number:
    - starts with "+"
    - contains only digits after "+"
    - has length between 10 and 15 digits

    Args:
        value (str): Phone number string to validate.

    Raises:
        ValidationError: If phone number format is invalid.
    """
    cleaned = value.replace(" ", "").replace("-", "")

    if not re.match(r"^\+\d{10,15}$", cleaned):
        raise ValidationError(
            _("Phone number must be in format: +380XXXXXXXXX"),
            code="invalid_phone",
        )


def validate_coordinates(latitude: float, longitude: float) -> None:
    """
    Validate geographic coordinates.
    Ensures:
    - latitude is between -90 and 90
    - longitude is between -180 and 180

    Args:
        latitude (float): Latitude value to validate.
        longitude (float): Longitude value to validate.

    Raises:
        ValidationError: If latitude or longitude is out of valid range.
    """
    if not -90 <= latitude <= 90:
        raise ValidationError(
            _("Latitude must be between -90 and 90"),
            code="invalid_latitude",
        )

    if not -180 <= longitude <= 180:
        raise ValidationError(
            _("Longitude must be between -180 and 180"),
            code="invalid_longitude",
        )


def validate_rating(value: int) -> None:
    """
    Validate rating value.
    Ensures rating is within allowed range (1–5).

    Args:
        value (int): Rating value to validate.

    Raises:
        ValidationError: If rating is outside allowed range.
    """
    if not 1 <= value <= 5:
        raise ValidationError(
            _("Rating must be between 1 and 5"),
            code="invalid_rating",
        )


def validate_file_size(file, max_size_mb: int = 10) -> None:
    """
    Validate uploaded file size.
    Ensures file does not exceed maximum allowed size.

    Args:
        file (File): Uploaded file object.
        max_size_mb (int, optional): Maximum allowed file size in megabytes.
            Defaults to 10 MB.

    Raises:
        ValidationError: If file size exceeds allowed limit.
    """
    max_size_bytes = max_size_mb * 1024 * 1024

    if file.size > max_size_bytes:
        raise ValidationError(
            _(f"File size must not exceed {max_size_mb}MB"),
            code="file_too_large",
        )


def validate_image_file(file) -> None:
    """
    Validate uploaded image file type.
    Ensures file extension is one of supported formats:
    .jpg, .jpeg, .png, .gif, .webp

    Args:
        file (File): Uploaded file object.

    Raises:
        ValidationError: If file extension is not supported.
    """
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

    ext = os.path.splitext(file.name)[1].lower()

    if ext not in valid_extensions:
        raise ValidationError(
            _(f"Invalid file type. Allowed: {', '.join(valid_extensions)}"),
            code="invalid_file_type",
        )