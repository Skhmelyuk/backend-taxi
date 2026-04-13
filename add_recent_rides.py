#!/usr/bin/env python3
"""Add recent test rides for driver-app testing."""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')
django.setup()

from datetime import timedelta
import random
from django.utils import timezone
from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.payments.models import Payment
from apps.users.models import User


def add_recent_rides():
    """Add 10 rides for the last 5 days."""
    driver = Driver.objects.filter(status='approved').first()
    if not driver:
        print('No approved driver found!')
        return

    passenger = User.objects.filter(is_passenger=True).first()
    if not passenger:
        print('No passenger found!')
        return

    now = timezone.now()
    total_added = 0

    for i in range(10):
        days_ago = random.randint(0, 5)
        created_at = now - timedelta(days=days_ago, hours=random.randint(0, 12))
        accepted_at = created_at + timedelta(seconds=random.randint(30, 300))
        completed_at = accepted_at + timedelta(minutes=random.randint(10, 45))

        ride = Ride.objects.create(
            user=passenger,
            driver=driver,
            status='completed',
            vehicle_type=driver.vehicle_type,
            pickup_location='POINT(30.523 50.450)',
            dropoff_location='POINT(30.600 50.480)',
            pickup_address='вул. Хрещатик, 1, Київ',
            dropoff_address='вул. Тестова, 55, Київ',
            estimated_distance=7.5,
            estimated_duration=20,
            estimated_price=120,
            final_distance=7.8,
            final_duration=22,
            final_price=125,
            rating=random.randint(3, 5),
            created_at=created_at,
            accepted_at=accepted_at,
            completed_at=completed_at,
        )

        payment_method = random.choice(['cash', 'card'])
        Payment.objects.create(
            ride=ride,
            user=passenger,
            amount=125,
            currency='UAH',
            status='success',
            payment_method=payment_method,
            provider='cash' if payment_method == 'cash' else 'liqpay',
            processed_at=completed_at,
        )
        total_added += 1

    # Update driver stats
    from django.db.models import Sum
    driver.total_rides = Ride.objects.filter(driver=driver, status='completed').count()
    driver.total_earnings = Ride.objects.filter(
        driver=driver, status='completed'
    ).aggregate(total=Sum('final_price'))['total'] or 0

    cash = Payment.objects.filter(
        ride__driver=driver, payment_method='cash', status='success'
    ).aggregate(t=Sum('amount'))['t'] or 0

    card = Payment.objects.filter(
        ride__driver=driver, payment_method='card', status='success'
    ).aggregate(t=Sum('amount'))['t'] or 0

    driver.cash_earnings = cash
    driver.card_earnings = card
    driver.pending_card_withdrawal = card
    driver.save()

    print(f'✓ Added {total_added} rides for last 5 days')
    print(f'  Total rides: {driver.total_rides}')
    print(f'  Cash: {driver.cash_earnings} UAH')
    print(f'  Card: {driver.card_earnings} UAH')


if __name__ == '__main__':
    add_recent_rides()
