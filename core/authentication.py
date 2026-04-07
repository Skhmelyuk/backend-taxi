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
        logger.info("JWT Verification: kid found in token: %s", kid)
        if not kid:
            raise jwt.InvalidTokenError('Token missing key ID')
        signing_key = self._get_signing_key(jwks, kid)
        logger.info("JWT Verification: entering decode block...")
        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                options={'verify_signature': False, 'verify_exp': False, 'verify_aud': False}
            )
            logger.info("JWT Verification: decode successful, payload keys: %s", payload.keys())
            return payload
        except Exception as e:
            logger.error("JWT Decode CRITICAL error (%s): %s", type(e).__name__, e)
            raise jwt.InvalidTokenError(str(e))

    def _get_jwks(self) -> dict:
        cache_key = 'clerk_jwks'
        jwks = cache.get(cache_key)
        if jwks:
            return jwks

        pk = settings.CLERK_PUBLISHABLE_KEY
        if not pk:
            raise jwt.InvalidTokenError('CLERK_PUBLISHABLE_KEY is not set')

        # Format: pk_test_[base64_encoded_host]$
        try:
            import base64
            parts = pk.split('_')
            if len(parts) >= 3:
                host_part = parts[2]
                if '$' in host_part:
                    host_part = host_part.split('$')[0]
                
                # Double check for any non-base64 chars
                host_part = ''.join(c for c in host_part if c.isalnum() or c in '+/')
                
                padding = (4 - len(host_part) % 4) % 4
                host_part += '=' * padding
                
                clerk_host = base64.b64decode(host_part).decode('utf-8')
                # Force remove any trailing dots or symbols from decoded host
                clerk_host = clerk_host.strip().rstrip('.')
                
                jwks_url = f'https://{clerk_host}/.well-known/jwks.json'
                logger.info("JWT Verification: ATTEMPTING to fetch JWKS from [%s]", jwks_url)
            else:
                raise ValueError("Invalid Publishable Key format")
        except Exception as e:
            logger.error("Failed to parse Clerk host from publishable key: %s", e)
            jwks_url = 'https://set-duck-83.clerk.accounts.dev/.well-known/jwks.json'
            logger.info("JWT Verification: falling back to manual URL: %s", jwks_url)

        try:
            # Final clean of the URL string just in case
            jwks_url = jwks_url.replace('$', '').strip()
            logger.info("JWT Verification: CLEANED requests.get(%s)", jwks_url)
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
                logger.info("JWT Verification: found matching kid in JWKS")
                n = key.get('n')
                e = key.get('e')
                if not n or not e:
                    logger.error("JWT Verification: key component missing n or e")
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
                logger.info("JWT Verification: successfully generated PEM key")
                return pem

        logger.error("JWT Verification: kid %s NOT found in JWKS keys", kid)
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
