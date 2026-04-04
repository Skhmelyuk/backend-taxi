import logging
from typing import Optional, Tuple

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()
logger = logging.getLogger(__name__)


class ClerkAuthentication(BaseAuthentication):
    """Custom authentication using Clerk JWT tokens."""

    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request) -> Optional[Tuple]:
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]

        try:
            payload = self._verify_token(token)
            user = self._get_or_create_user(payload)
            user.update_last_login()
            logger.info("User authenticated: %s", user.email)
            return (user, None)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            logger.error("Authentication error: %s", e, exc_info=True)
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')

    def _verify_token(self, token: str) -> dict:
        jwks = self._get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        if not kid:
            raise jwt.InvalidTokenError('Token missing key ID')
        signing_key = self._get_signing_key(jwks, kid)
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=['RS256'],
            audience=settings.CLERK_PUBLISHABLE_KEY,
            options={'verify_signature': True, 'verify_exp': True, 'verify_aud': True}
        )
        return payload

    def _get_jwks(self) -> dict:
        cache_key = 'clerk_jwks'
        jwks = cache.get(cache_key)
        if jwks:
            return jwks
    
        jwks_url = 'https://aware-owl-72.clerk.accounts.dev/.well-known/jwks.json'
    
        try:
            response = requests.get(jwks_url, timeout=5)
            response.raise_for_status()
            jwks = response.json()
            cache.set(cache_key, jwks, timeout=3600)
            return jwks
        except requests.RequestException as e:
            logger.error("Failed to fetch JWKS: %s", e)
            raise jwt.InvalidTokenError('Unable to fetch JWKS') from e

    def _get_signing_key(self, jwks: dict, kid: str):
        import base64

        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                n = key.get('n')
                e = key.get('e')
                if not n or not e:
                    raise jwt.InvalidTokenError('Invalid key format')
                n_bytes = base64.urlsafe_b64decode(n + '==')
                e_bytes = base64.urlsafe_b64decode(e + '==')
                n_int = int.from_bytes(n_bytes, byteorder='big')
                e_int = int.from_bytes(e_bytes, byteorder='big')
                public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
                public_key = public_numbers.public_key(default_backend())
                pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                return pem

        raise jwt.InvalidTokenError(f'Unable to find signing key with kid: {kid}')

    def _get_or_create_user(self, payload: dict) -> User:
        clerk_user_id = payload.get('sub')
        email = payload.get('email')

        if not clerk_user_id:
            raise AuthenticationFailed('Token missing user ID')

        try:
            return User.objects.get(clerk_user_id=clerk_user_id)
        except User.DoesNotExist:
            pass

        if email:
            try:
                user = User.objects.get(email=email)
                user.clerk_user_id = clerk_user_id
                user.save(update_fields=['clerk_user_id'])
                return user
            except User.DoesNotExist:
                pass

        if not email:
            raise AuthenticationFailed('Token missing email')

        return User.objects.create_user(
            email=email,
            clerk_user_id=clerk_user_id,
            first_name=payload.get('given_name') or '',
            last_name=payload.get('family_name') or '',
            is_verified=payload.get('email_verified', False)
        )
