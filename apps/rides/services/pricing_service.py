"""
Pricing service for calculating ride fares based on distance, duration, vehicle type, and surge pricing. 
"""

import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


PRICING_CONFIG = {
    'economy': {
        'base_fare': Decimal('30.0'),
        'per_km': Decimal('9.0'),
        'per_minute': Decimal('2.5'),
        'min_fare': Decimal('50.0'),
    },
    'comfort': {
        'base_fare': Decimal('50.0'),
        'per_km': Decimal('14.0'),
        'per_minute': Decimal('3.5'),
        'min_fare': Decimal('80.0'),
    },
    'business': {
        'base_fare': Decimal('80.0'),
        'per_km': Decimal('20.0'),
        'per_minute': Decimal('5.0'),
        'min_fare': Decimal('120.0'),
    },
}

AVG_SPEED_KMH = 30.0


class PricingService:

    @staticmethod
    def calculate_distance(
        pickup_lat: float, pickup_lon: float,
        dropoff_lat: float, dropoff_lon: float
    ) -> float:
        """Calculate distance in km using PostGIS or Haversine fallback."""
        try:
            from django.contrib.gis.geos import Point
            from django.contrib.gis.measure import Distance
            p1 = Point(pickup_lon, pickup_lat, srid=4326)
            p2 = Point(dropoff_lon, dropoff_lat, srid=4326)
            # Haversine via GIS
            import math
            R = 6371.0
            lat1, lon1 = math.radians(pickup_lat), math.radians(pickup_lon)
            lat2, lon2 = math.radians(dropoff_lat), math.radians(dropoff_lon)
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return round(R * c, 2)
        except Exception as e:
            logger.error(f"Distance calculation error: {e}")
            return 5.0

    @staticmethod
    def calculate_price(distance_km: float, vehicle_type: str, surge_multiplier: float = 1.0) -> dict:
        """Calculate ride price."""
        config = PRICING_CONFIG.get(vehicle_type, PRICING_CONFIG['economy'])
        duration_minutes = round(distance_km / AVG_SPEED_KMH * 60)

        price = (
            config['base_fare']
            + Decimal(str(distance_km)) * config['per_km']
            + Decimal(str(duration_minutes)) * config['per_minute']
        )

        price *= Decimal(str(surge_multiplier))
        price = max(price, config['min_fare'])
        price = price.quantize(Decimal('0.01'))

        return {
            'distance_km': distance_km,
            'duration_minutes': duration_minutes,
            'base_fare': float(config['base_fare']),
            'per_km_rate': float(config['per_km']),
            'estimated_price': float(price),
            'vehicle_type': vehicle_type,
            'surge_multiplier': surge_multiplier,
        }

    @staticmethod
    def get_price_estimate(
        pickup_lat: float, pickup_lon: float,
        dropoff_lat: float, dropoff_lon: float,
        vehicle_type: str,
        surge_multiplier: float = 1.0
    ) -> dict:
        """Get full price estimate including distance calculation."""
        distance_km = PricingService.calculate_distance(
            pickup_lat, pickup_lon, dropoff_lat, dropoff_lon
        )
        return PricingService.calculate_price(distance_km, vehicle_type, surge_multiplier)

    @staticmethod
    def get_surge_multiplier() -> float:
        """Get current surge pricing multiplier (1.0 = normal)."""
        from django.core.cache import cache
        return cache.get('surge_multiplier', 1.0)

    @staticmethod
    def apply_promo_code(price: Decimal, promo_code) -> tuple:
        """Apply promo code discount. Returns (discounted_price, discount_amount)."""
        try:
            if not promo_code or not promo_code.is_valid:
                return price, Decimal('0')
            discount = price * (promo_code.discount_percent / 100)
            discount = min(discount, promo_code.max_discount or discount)
            return max(price - discount, Decimal('0')), discount
        except Exception as e:
            logger.warning(f"Promo code error: {e}")
            return price, Decimal('0')