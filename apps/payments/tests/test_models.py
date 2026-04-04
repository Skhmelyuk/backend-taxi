import pytest
from decimal import Decimal
from django.utils import timezone
from apps.payments.models import Payment, PromoCode
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestPromoCode:

    def test_valid_promo_code(self):
        promo = PromoCode.objects.create(
            code='TEST10', discount_percent=10, is_active=True
        )
        assert promo.is_valid is True

    def test_expired_promo_code(self):
        from datetime import timedelta
        promo = PromoCode.objects.create(
            code='EXPIRED10', discount_percent=10,
            valid_until=timezone.now() - timedelta(days=1)
        )
        assert promo.is_valid is False

    def test_usage_limit_reached(self):
        promo = PromoCode.objects.create(
            code='LIMIT10', discount_percent=10,
            usage_limit=5, usage_count=5
        )
        assert promo.is_valid is False