"""
Business logic services for users app.
"""

import logging
from typing import Optional

from apps.users.models import User

logger = logging.getLogger(__name__)


def handle_clerk_user_created(data: dict) -> None:
    """Handle Clerk user.created event."""
    clerk_user_id = data.get('id')
    email_addresses = data.get('email_addresses', [])
    primary_email_id = data.get('primary_email_address_id')

    email: Optional[str] = None
    for addr in email_addresses:
        if addr.get('id') == primary_email_id:
            email = addr.get('email_address')
            break

    if not email:
        logger.warning("No email found for Clerk user: %s", clerk_user_id)
        return

    try:
        user = User.objects.get(clerk_user_id=clerk_user_id)
        logger.info("User already exists: %s", user.email)
    except User.DoesNotExist:
        user = User.objects.create_user(
            email=email,
            clerk_user_id=clerk_user_id,
            first_name=data.get('first_name') or '',
            last_name=data.get('last_name') or '',
        )
        logger.info("Created user from webhook: %s", user.email)


def handle_clerk_user_updated(data: dict) -> None:
    """Handle Clerk user.updated event."""
    clerk_user_id = data.get('id')
    try:
        user = User.objects.get(clerk_user_id=clerk_user_id)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.save(update_fields=['first_name', 'last_name', 'updated_at'])
        logger.info("Updated user from webhook: %s", user.email)
    except User.DoesNotExist:
        logger.warning("User not found for webhook update: %s", clerk_user_id)


def handle_clerk_user_deleted(data: dict) -> None:
    """Handle Clerk user.deleted event."""
    clerk_user_id = data.get('id')
    try:
        user = User.objects.get(clerk_user_id=clerk_user_id)
        user.is_active = False
        user.save(update_fields=['is_active', 'updated_at'])
        logger.info("Deactivated user from webhook: %s", user.email)
    except User.DoesNotExist:
        logger.warning("User not found for webhook delete: %s", clerk_user_id)
