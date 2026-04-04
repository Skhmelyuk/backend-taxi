"""
Tests for PromoCodeService.
"""

import pytest
from decimal import Decimal

from apps.payments.models import PromoCode
from apps.payments.services import PromoCodeService


@pytest.mark.django_db
class TestPromoCodeService:

    def test_validate_valid_promo(self) -> None:
        """Test validating a valid promo code."""
        PromoCode.objects.create(
            code='TEST20', discount_percent=Decimal('20'), is_active=True
        )
        discount, promo = PromoCodeService.validate_promo_code('TEST20', Decimal('100'))
        assert discount == Decimal('20')

    def test_validate_nonexistent_promo(self) -> None:
        """Test validating a non-existent promo code."""
        with pytest.raises(ValueError, match='not found'):
            PromoCodeService.validate_promo_code('NOTEXIST', Decimal('100'))

    def test_validate_below_min_price(self) -> None:
        """Test validating a promo code when ride price is below minimum."""
        PromoCode.objects.create(
            code='MINPRICE',
            discount_percent=Decimal('10'),
            min_ride_price=Decimal('200'),
            is_active=True,
        )
        with pytest.raises(ValueError, match='Minimum ride price'):
            PromoCodeService.validate_promo_code('MINPRICE', Decimal('100'))

    def test_max_discount_cap(self) -> None:
        """Test that discount does not exceed max_discount."""
        PromoCode.objects.create(
            code='MAXTEST',
            discount_percent=Decimal('50'),
            max_discount=Decimal('30'),
            is_active=True,
        )
        discount, _ = PromoCodeService.validate_promo_code('MAXTEST', Decimal('200'))
        assert discount == Decimal('30')

    def test_apply_increments_usage(self) -> None:
        """Test that applying a promo code increments its usage count."""
        promo = PromoCode.objects.create(
            code='USAGE10', discount_percent=Decimal('10'), is_active=True
        )
        PromoCodeService.apply_promo_code('USAGE10', Decimal('100'))
        promo.refresh_from_db()
        assert promo.usage_count == 1

    def test_validate_inactive_promo(self) -> None:
        PromoCode.objects.create(code='INACTIVE', discount_percent=Decimal('20'), is_active=False)
        with pytest.raises(ValueError, match='expired or inactive'):
            PromoCodeService.validate_promo_code('INACTIVE', Decimal('100'))

    def test_calculate_discount_fixed_amount(self) -> None:
        promo = PromoCode.objects.create(
            code='FIXED', discount_type=PromoCode.DiscountType.FIXED, discount_amount=Decimal('25'), is_active=True
        )
        discount = PromoCodeService.calculate_discount(Decimal('100'), promo)
        assert discount == Decimal('25')
        
        # Test capping logic when price is lower than fixed discount
        discount_capped = PromoCodeService.calculate_discount(Decimal('10'), promo)
        assert discount_capped == Decimal('10')
