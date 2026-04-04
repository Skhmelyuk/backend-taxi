"""Notification message templates."""

from typing import Dict, Optional


NOTIFICATION_TEMPLATES = {
    'ride_created': {
        'title': 'Looking for a driver...',
        'message': 'We are finding the best driver for you',
    },
    'ride_accepted': {
        'title': 'Driver Found! 🚗',
        'message': '{driver_name} is on the way. ETA: {eta_minutes} min',
    },
    'ride_started': {
        'title': 'Ride Started! 🚀',
        'message': 'Your trip has started. Enjoy the ride!',
    },
    'ride_completed': {
        'title': 'Ride Completed ✅',
        'message': 'You arrived! Total: {final_price} UAH',
    },
    'ride_cancelled': {
        'title': 'Ride Cancelled',
        'message': 'Your ride was cancelled',
    },
    'driver_arrived': {
        'title': 'Driver Arrived! 📍',
        'message': '{driver_name} is waiting at your pickup location',
    },
    'payment_success': {
        'title': 'Payment Successful 💳',
        'message': 'Payment of {amount} UAH confirmed',
    },
    'payment_failed': {
        'title': 'Payment Failed ❌',
        'message': 'Your payment could not be processed',
    },
    'refund_processed': {
        'title': 'Refund Processed 💰',
        'message': '{amount} UAH will be returned to your account',
    },
    'new_ride_request': {
        'title': 'New Ride Request! 🏁',
        'message': 'Pickup: {pickup_address}',
    },
    'promo_available': {
        'title': 'Special Offer! 🎉',
        'message': 'Use promo code {code} for {discount}% off',
    },
}


def get_notification_content(notification_type: str, context: Optional[Dict] = None) -> Dict:
    """
    Get notification title and message with context substitution.

    Args:
        notification_type: One of NOTIFICATION_TEMPLATES keys
        context: Variables to substitute in template strings

    Returns:
        {'title': ..., 'message': ...}
    """
    template = NOTIFICATION_TEMPLATES.get(notification_type)
    if not template:
        return {
            'title': 'Notification',
            'message': f'Event: {notification_type}',
        }

    context = context or {}
    try:
        return {
            'title': template['title'].format(**context),
            'message': template['message'].format(**context),
        }
    except KeyError:
        return {
            'title': template['title'],
            'message': template['message'],
        }
