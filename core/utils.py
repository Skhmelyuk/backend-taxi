import hashlib
import secrets
from datetime import datetime
from typing import Optional
import re
from django.utils import timezone


def generate_unique_code(length: int = 8) -> str:
    """
    Generate a secure random uppercase code of specified length.
    Uses URL-safe random generator and trims to requested length.

    Args:
        length (int, optional): Length of generated code. Defaults to 8.

    Returns:
        str: Secure random uppercase string.
    """
    return secrets.token_urlsafe(length)[:length].upper()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two geographic coordinates using Haversine formula.
    Distance is calculated in kilometers.

    Args:
        lat1 (float): Latitude of first location.
        lon1 (float): Longitude of first location.
        lat2 (float): Latitude of second location.
        lon2 (float): Longitude of second location.

    Returns:
        float: Distance in kilometers rounded to 2 decimal places.
    """
    from math import radians, sin, cos, sqrt, atan2

    R = 6371  # Earth radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(R * c, 2)


def hash_string(value: str) -> str:
    """
    Generate SHA256 hash of input string.
    Useful for secure token storage, verification hashes, etc.

    Args:
        value (str): Input string to hash.

    Returns:
        str: SHA256 hash in hexadecimal format.
    """
    return hashlib.sha256(value.encode()).hexdigest()


def get_client_ip(request) -> Optional[str]:
    """
    Extract client IP address from Django request.
    Supports proxy headers (X-Forwarded-For) and direct connection.

    Args:
        request (Request): Django request object.

    Returns:
        Optional[str]: Client IP address or None if not available.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]

    return request.META.get("REMOTE_ADDR")


def format_phone_number(phone: str) -> str:
    """
    Format phone number to standardized international format.
    Removes non-digit characters and ensures "+" prefix.
    Args:
        phone (str): Raw phone number string.

    Returns:
        str: Formatted phone number with "+" prefix.
    """
    digits = "".join(filter(str.isdigit, phone))

    if not phone.startswith("+"):
        digits = "+" + digits

    return digits


def time_ago(dt: datetime) -> str:
    """
    Convert datetime to human-readable relative time string.
    Examples:
        "just now"
        "5 minutes ago"
        "2 hours ago"
        "3 days ago"
        "1 week ago"

    Args:
        dt (datetime): Datetime to compare with current time.

    Returns:
        str: Human-readable relative time string.
    """
    now = timezone.now()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"

    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = int(seconds / 86400)

    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"

    weeks = int(days / 7)
    return f"{weeks} week{'s' if weeks != 1 else ''} ago"


def is_valid_email(email: str) -> bool:
    """
    Validate email format using regular expression.
    Checks basic email structure: username@domain.extension

    Args:
        email (str): Email address to validate.

    Returns:
        bool: True if email format is valid, False otherwise.
    """
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(email_regex, email) is not None