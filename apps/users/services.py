"""
Business logic services for users app.
"""

import logging
from typing import Optional

from apps.users.models import User
from apps.drivers.services import DriverService
from apps.drivers.models import Driver

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
    
    # Fallback to phone-based email if no email is provided (phone-only auth)
    public_metadata = data.get('public_metadata', {})
    unsafe_metadata = data.get('unsafe_metadata', {})
    phone_number = public_metadata.get('phone_number') or unsafe_metadata.get('phone_number')
    
    if not email:
        if phone_number:
            email = f"phone_{phone_number.replace('+', '')}@clerk.user"
        else:
            email = f"user_{clerk_user_id}@clerk.user"
        logger.info("Generated placeholder email for phone-only user: %s", email)

    first_name = data.get('first_name')
    last_name = data.get('last_name')
    
    # Check metadata for names if root is empty
    if not first_name:
        first_name = unsafe_metadata.get('first_name') or public_metadata.get('first_name') or ''
    if not last_name:
        last_name = unsafe_metadata.get('last_name') or public_metadata.get('last_name') or ''

    try:
        user = User.objects.get(clerk_user_id=clerk_user_id)
        logger.info("User already exists: %s", user.email)
    except User.DoesNotExist:
        # Check if user with this email already exists (maybe created during auth)
        user = User.objects.filter(email=email).first()
        if user:
            user.clerk_user_id = clerk_user_id
            user.save(update_fields=['clerk_user_id'])
            logger.info("Linked existing user by email: %s", user.email)
        else:
            user = User.objects.create_user(
                email=email,
                clerk_user_id=clerk_user_id,
                first_name=first_name,
                last_name=last_name,
            )
            logger.info("Created user from webhook: %s", user.email)

    public_metadata = data.get('public_metadata', {})
    unsafe_metadata = data.get('unsafe_metadata', {})
    phone_number = public_metadata.get('phone_number') or unsafe_metadata.get('phone_number')
    role = public_metadata.get('role')

    updates = []

    if first_name and user.first_name != first_name:
        user.first_name = first_name
        updates.append('first_name')

    if last_name and user.last_name != last_name:
        user.last_name = last_name
        updates.append('last_name')

    profile_image = data.get('image_url') or data.get('profile_image_url')
    if profile_image and user.profile_image != profile_image:
        user.profile_image = profile_image
        updates.append('profile_image')

    if email and user.email != email:
        user.email = email
        updates.append('email')

    if phone_number and user.phone_number != phone_number:
        user.phone_number = phone_number
        updates.append('phone_number')

    # Determine role: respect intended_role from driver app, or existing public_metadata role.
    intended_role = unsafe_metadata.get('intended_role')
    
    if role == User.Role.DRIVER or intended_role == 'driver':
        if user.role != User.Role.DRIVER:
            user.role = User.Role.DRIVER
            updates.append('role')
            # Push publicMetadata.role=driver to Clerk so JWT claims are updated
            if role != User.Role.DRIVER:
                _set_clerk_user_role_driver(clerk_user_id)
    else:
        # For all other cases (e.g. client app registration), default to USER
        if not user.role:
            user.role = User.Role.USER
            updates.append('role')

    created_driver = False
    if user.role == User.Role.DRIVER and not hasattr(user, 'driver_profile'):
        try:
            DriverService.register_driver(user)
            created_driver = True
        except ValueError:
            logger.info("Driver profile already exists for user %s", user.email)
        except Exception as exc:
            logger.error("Failed to auto-create driver profile for %s: %s", user.email, exc)

    if updates:
        user.save(update_fields=updates)
        logger.info(
            "Updated user metadata for %s: %s",
            user.email,
            ', '.join(updates),
        )

    if created_driver:
        logger.info("Auto-created driver profile for %s", user.email)



def handle_clerk_user_updated(data: dict) -> None:
    """Handle Clerk user.updated event."""
    clerk_user_id = data.get('id')
    try:
        user = User.objects.get(clerk_user_id=clerk_user_id)
        updates = []

        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        # Consolidation: check metadata if root names are empty
        unsafe_metadata = data.get('unsafe_metadata', {})
        public_metadata = data.get('public_metadata', {})
        
        if not first_name:
            first_name = unsafe_metadata.get('first_name') or public_metadata.get('first_name')
        if not last_name:
            last_name = unsafe_metadata.get('last_name') or public_metadata.get('last_name')

        email_addresses = data.get('email_addresses', [])
        primary_email_id = data.get('primary_email_address_id')

        if first_name is not None and first_name != user.first_name:
            user.first_name = first_name
            updates.append('first_name')

        if last_name is not None and last_name != user.last_name:
            user.last_name = last_name
            updates.append('last_name')

        profile_image = data.get('image_url') or data.get('profile_image_url')
        if profile_image and user.profile_image != profile_image:
            user.profile_image = profile_image
            updates.append('profile_image')

        if primary_email_id:
            for addr in email_addresses:
                if addr.get('id') == primary_email_id:
                    email = addr.get('email_address')
                    if email and email != user.email:
                        user.email = email
                        updates.append('email')
                    break

        phone_number = public_metadata.get('phone_number') or unsafe_metadata.get('phone_number')
        intended_role = unsafe_metadata.get('intended_role')
        role = public_metadata.get('role')

        logger.info(
            "Webhook user.updated for %s: role=%s, intended_role=%s",
            user.email, role, intended_role
        )

        if phone_number and user.phone_number != phone_number:
            user.phone_number = phone_number
            updates.append('phone_number')

        if (role == User.Role.DRIVER or intended_role == 'driver') and user.role != User.Role.DRIVER:
            user.role = User.Role.DRIVER
            updates.append('role')
            logger.info("Setting role to DRIVER for user %s based on %s", user.email, 
                        "metadata role" if role == User.Role.DRIVER else "intended_role")
            if role != User.Role.DRIVER:
                _set_clerk_user_role_driver(clerk_user_id)

        if updates:
            update_fields = updates + ['updated_at']
            user.save(update_fields=update_fields)
            logger.info("Saved updates for %s: %s", user.email, ', '.join(updates))

        if user.role == User.Role.DRIVER and not hasattr(user, 'driver_profile'):
            try:
                logger.info("Auto-creating driver profile for %s...", user.email)
                DriverService.register_driver(user)
                logger.info("Successfully created driver profile for %s", user.email)
            except ValueError:
                logger.info("Driver profile already exists for user %s", user.email)
            except Exception as exc:
                logger.error("Failed to auto-create driver profile for %s: %s", user.email, exc)
        else:
            logger.info("Skipping driver profile creation for %s: role=%s, has_profile=%s", 
                        user.email, user.role, hasattr(user, 'driver_profile'))
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
