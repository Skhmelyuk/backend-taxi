import pytest
from decimal import Decimal
from apps.rides.services.pricing_service import PricingService


class TestPricingService:

    def test_calculate_distance(self):
        distance = PricingService.calculate_distance(50.4501, 30.5234, 50.4313, 30.4879)
        assert 2.0 < distance < 8.0

    def test_calculate_price_economy(self):
        result = PricingService.calculate_price(5.0, 'economy')
        assert result['estimated_price'] >= 50.0  # min fare
        assert result['distance_km'] == 5.0
        assert result['vehicle_type'] == 'economy'

    def test_minimum_fare_applied(self):
        result = PricingService.calculate_price(0.1, 'economy')
        assert result['estimated_price'] == 50.0  # min fare

    def test_surge_multiplier(self):
        normal = PricingService.calculate_price(5.0, 'economy', surge_multiplier=1.0)
        surge = PricingService.calculate_price(5.0, 'economy', surge_multiplier=2.0)
        assert surge['estimated_price'] > normal['estimated_price']

    def test_business_more_expensive_than_economy(self):
        economy = PricingService.calculate_price(5.0, 'economy')
        business = PricingService.calculate_price(5.0, 'business')
        assert business['estimated_price'] > economy['estimated_price']

    def test_calculate_distance_exception(self, monkeypatch):
        """Test fallback when distance calculation raises an exception"""
        monkeypatch.setattr('math.radians', lambda x: 1/0)  # trigger exception
        distance = PricingService.calculate_distance(50.4501, 30.5234, 50.4313, 30.4879)
        assert distance == 5.0

    def test_get_surge_multiplier(self, monkeypatch):
        """Test surge multiplier retrieval from cache"""
        monkeypatch.setattr('django.core.cache.cache.get', lambda key, default: 1.5 if key == 'surge_multiplier' else default)
        assert PricingService.get_surge_multiplier() == 1.5

    def test_apply_promo_code_no_promo_or_invalid(self):
        """Test applying promo code when none is provided or when promo is invalid."""
        class MockPromo:
            is_valid = False
            
        price, discount = PricingService.apply_promo_code(Decimal('100.0'), None)
        assert price == Decimal('100.0')
        assert discount == Decimal('0')

        price, discount = PricingService.apply_promo_code(Decimal('100.0'), MockPromo())
        assert price == Decimal('100.0')
        assert discount == Decimal('0')

    def test_apply_promo_code_valid(self):
        """Test applying a valid promo code with percentage discount and max discount."""
        class MockPromo:
            is_valid = True
            discount_percent = Decimal('20')
            max_discount = Decimal('15.0')
            
        # 100 * 20% = 20, but max_discount is 15
        price, discount = PricingService.apply_promo_code(Decimal('100.0'), MockPromo())
        assert price == Decimal('85.0')
        assert discount == Decimal('15.0')

        class MockPromoNoMax:
            is_valid = True
            discount_percent = Decimal('20')
            max_discount = None

        # 100 * 20% = 20
        price, discount = PricingService.apply_promo_code(Decimal('100.0'), MockPromoNoMax())
        assert price == Decimal('80.0')
        assert discount == Decimal('20.0')

    def test_apply_promo_code_exception(self):
        """Test that exceptions in promo code validation are handled gracefully."""
        class MockPromoBad:
            @property
            def is_valid(self):
                raise Exception("DB query failed")

        price, discount = PricingService.apply_promo_code(Decimal('100.0'), MockPromoBad())
        assert price == Decimal('100.0')
        assert discount == Decimal('0')