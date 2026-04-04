import logging
from typing import List, Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class FCMService:
    """Firebase Cloud Messaging service."""

    _app = None

    @classmethod
    def _get_app(cls):
        """Initialize Firebase app (singleton)."""
        if cls._app is not None:
            return cls._app

        credentials_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', '')
        if not credentials_path:
            logger.warning("FIREBASE_CREDENTIALS_PATH not set — FCM disabled")
            return None

        try:
            import firebase_admin
            from firebase_admin import credentials
            cred = credentials.Certificate(credentials_path)
            cls._app = firebase_admin.initialize_app(cred)
            logger.info("Firebase app initialized")
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            cls._app = None

        return cls._app

    @classmethod
    def send_notification(
        cls,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> bool:
        """Send push notification to single device."""
        app = cls._get_app()
        if not app:
            logger.warning(f"FCM not initialized — skipping notification to {token[:20]}...")
            return False

        try:
            from firebase_admin import messaging
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={str(k): str(v) for k, v in (data or {}).items()},
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"FCM sent: {response}")
            return True
        except Exception as e:
            logger.error(f"FCM send failed: {e}")
            return False

    @classmethod
    def send_multicast(
        cls,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> Dict:
        """Send push notification to multiple devices."""
        app = cls._get_app()
        if not app:
            logger.warning("FCM not initialized — skipping multicast")
            return {'success': 0, 'failure': len(tokens)}

        try:
            from firebase_admin import messaging
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data={str(k): str(v) for k, v in (data or {}).items()},
                tokens=tokens,
            )
            response = messaging.send_multicast(message)
            logger.info(
                f"FCM multicast: {response.success_count} ok, {response.failure_count} fail"
            )
            return {
                'success': response.success_count,
                'failure': response.failure_count,
            }
        except Exception as e:
            logger.error(f"FCM multicast failed: {e}")
            return {'success': 0, 'failure': len(tokens)}

    @classmethod
    def send_to_user(cls, user, title: str, body: str, data: Optional[Dict] = None) -> Dict:
        """Send notification to all user devices."""
        tokens = list(
            user.devices.filter(is_active=True).values_list('fcm_token', flat=True)
        )
        if not tokens:
            # Fallback: use FCM token from User model
            if user.fcm_token:
                tokens = [user.fcm_token]

        if not tokens:
            logger.info(f"No FCM tokens for user {user.email}")
            return {'success': 0, 'failure': 0}

        if len(tokens) == 1:
            success = cls.send_notification(tokens[0], title, body, data)
            return {'success': int(success), 'failure': int(not success)}

        return cls.send_multicast(tokens, title, body, data)
