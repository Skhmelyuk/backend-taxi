"""
Business logic services for users app.
"""

import logging
from typing import Optional

from apps.users.models import User

logger = logging.getLogger(__name__)


def _set_clerk_user_role_driver(clerk_user_id: str) -> None:
    """Call Clerk Backend API to set publicMetadata.role = 'driver'."""
    from django.conf import settings
    import urllib.request
    import json as json_module

    secret_key = getattr(settings, 'CLERK_SECRET_KEY', '')
    if not secret_key:
        logger.warning("CLERK_SECRET_KEY not set — cannot update publicMetadata via API")
        return

    url = f"https://api.clerk.com/v1/users/{clerk_user_id}/metadata"
    payload = json_module.dumps({"public_metadata": {"role": "driver"}}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req) as response:
            logger.info(
                "Set Clerk publicMetadata role=driver for user %s (status %s)",
                clerk_user_id, response.status,
            )
    except Exception as e:
        logger.error("Failed to set Clerk publicMetadata for %s: %s", clerk_user_id, e)


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

    public_metadata = data.get('public_metadata', {})
    unsafe_metadata = data.get('unsafe_metadata', {})
    phone_number = public_metadata.get('phone_number') or unsafe_metadata.get('phone_number')
    role = public_metadata.get('role')

    updates = []

    if phone_number and user.phone_number != phone_number:
        user.phone_number = phone_number
        updates.append('phone_number')

    # Role comes from publicMetadata set by Clerk Backend API (not the client).
    # If role is not yet 'driver' — set it now via Clerk API and update Django user.
    if role == User.Role.DRIVER and user.role != User.Role.DRIVER:
        user.role = User.Role.DRIVER
        updates.append('role')
    elif user.role != User.Role.DRIVER:
        # Driver app always creates drivers — set the role via Clerk Backend API
        user.role = User.Role.DRIVER
        updates.append('role')
        # Push publicMetadata.role=driver to Clerk so JWT claims are updated
        _set_clerk_user_role_driver(clerk_user_id)

    if updates:
        user.save(update_fields=updates)
        logger.info(
            "Updated user metadata for %s: %s",
            user.email,
            ', '.join(updates),
        )



def handle_clerk_user_updated(data: dict) -> None:
    """Handle Clerk user.updated event."""
    clerk_user_id = data.get('id')
    try:
        user = User.objects.get(clerk_user_id=clerk_user_id)
        updates = []

        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email_addresses = data.get('email_addresses', [])
        primary_email_id = data.get('primary_email_address_id')
        public_metadata = data.get('public_metadata', {})

        if first_name is not None and first_name != user.first_name:
            user.first_name = first_name
            updates.append('first_name')

        if last_name is not None and last_name != user.last_name:
            user.last_name = last_name
            updates.append('last_name')

        if primary_email_id:
            for addr in email_addresses:
                if addr.get('id') == primary_email_id:
                    email = addr.get('email_address')
                    if email and email != user.email:
                        user.email = email
                        updates.append('email')
                    break

        phone_number = public_metadata.get('phone_number')
        role = public_metadata.get('role')

        if phone_number and user.phone_number != phone_number:
            user.phone_number = phone_number
            updates.append('phone_number')

        if role == User.Role.DRIVER and user.role != User.Role.DRIVER:
            user.role = User.Role.DRIVER
            updates.append('role')

        if updates:
            update_fields = updates + ['updated_at']
            user.save(update_fields=update_fields)
            logger.info(
                "Updated user from webhook: %s (%s)",
                user.email,
                ', '.join(updates),
            )
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
