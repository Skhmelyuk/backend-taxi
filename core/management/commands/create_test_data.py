"""
Management command to create test data.
"""

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.gis.geos import Point

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test data for development: users, drivers, rides with ratings'

    def add_arguments(self, parser):
        parser.add_argument('--rides', type=int, default=30, help='Number of rides to create per driver')
        parser.add_argument('--clear', action='store_true', help='Clear existing test data before seeding')
        parser.add_argument(
            '--driver', type=str, dest='driver_emails',
            help='Comma-separated emails of existing drivers to seed rides for (e.g. john@example.com,jane@example.com)'
        )
        parser.add_argument('--all-drivers', action='store_true', help='Seed rides for ALL existing drivers')

    def _seed_rides_for_drivers(self, drivers, rides_count, passengers):
        from apps.rides.models import Ride

        now = timezone.now()
        pickup = Point(30.523, 50.450, srid=4326)
        dropoff = Point(30.600, 50.480, srid=4326)
        total_created = 0

        for driver in drivers:
            existing = Ride.objects.filter(driver=driver).count()
            if existing >= rides_count:
                self.stdout.write(self.style.WARNING(
                    f'  ! {driver.user.email} вже має {existing} поїздок, пропускаємо'
                ))
                continue

            rating_sum = 0.0
            count = 0
            for _ in range(rides_count - existing):
                created_at = now - timedelta(days=random.randint(0, 89), hours=random.randint(0, 23))
                accepted_at = created_at + timedelta(seconds=random.randint(30, 300))
                started_at = accepted_at + timedelta(minutes=random.randint(2, 8))
                completed_at = started_at + timedelta(minutes=random.randint(10, 45))
                ride_rating = random.randint(3, 5)

                Ride.objects.create(
                    user=random.choice(passengers),
                    driver=driver,
                    status=Ride.Status.COMPLETED,
                    vehicle_type=driver.vehicle_type,
                    pickup_location=pickup,
                    dropoff_location=dropoff,
                    pickup_address='вул. Хрещатик, 1, Київ',
                    dropoff_address='вул. Велика Васильківська, 55, Київ',
                    estimated_distance=7.5,
                    estimated_duration=20,
                    estimated_price=120,
                    final_distance=7.8,
                    final_duration=22,
                    final_price=125,
                    rating=ride_rating,
                    created_at=created_at,
                    accepted_at=accepted_at,
                    started_at=started_at,
                    completed_at=completed_at,
                )
                rating_sum += ride_rating
                count += 1
                total_created += 1

            if count > 0:
                driver.total_rides = Ride.objects.filter(driver=driver, status=Ride.Status.COMPLETED).count()
                driver.rating = round(rating_sum / count, 2)
                driver.save(update_fields=['rating', 'total_rides'])

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {driver.user.email} | +{count} поїздок | rating={driver.rating} total={driver.total_rides}'
            ))

        return total_created

    def handle(self, *args, **options):
        from apps.drivers.models import Driver, DriverDocument
        from apps.rides.models import Ride
        from apps.payments.models import Payment

        rides_count = options['rides']
        driver_emails = options.get('driver_emails')
        all_drivers = options.get('all_drivers')

        if options['clear']:
            self.stdout.write('Clearing existing test data...')
            from apps.payments.models import Payment as _P
            # Delete in correct FK order
            test_rides = Ride.objects.filter(
                user__email__endswith='@testpassenger.dev'
            )
            _P.objects.filter(ride__in=test_rides).delete()
            test_rides.delete()
            Driver.objects.filter(user__email__endswith='@testdriver.dev').delete()
            User.objects.filter(email__endswith='@testdriver.dev').delete()
            User.objects.filter(email__endswith='@testpassenger.dev').delete()
            self.stdout.write(self.style.WARNING('✓ Cleared'))

        # ── Mode: seed existing drivers ───────────────────────────────────────
        if driver_emails or all_drivers:
            passengers = list(User.objects.filter(role='user')[:10])
            if not passengers:
                passengers = list(User.objects.filter(email__endswith='@testpassenger.dev'))
            if not passengers:
                self.stdout.write(self.style.ERROR('Немає пасажирів у базі. Спочатку запустіть без --driver щоб створити тестових пасажирів.'))
                return

            if all_drivers:
                drivers = list(Driver.objects.select_related('user').all())
                self.stdout.write(f'Seeding {len(drivers)} drivers...')
            else:
                emails = [e.strip() for e in driver_emails.split(',')]
                drivers = list(Driver.objects.select_related('user').filter(user__email__in=emails))
                found = [d.user.email for d in drivers]
                missing = [e for e in emails if e not in found]
                if missing:
                    self.stdout.write(self.style.WARNING(f'  ! Не знайдено: {", ".join(missing)}'))

            total = self._seed_rides_for_drivers(drivers, rides_count, passengers)
            self.stdout.write(self.style.SUCCESS(f'\n✓ Готово! Додано {total} поїздок.'))
            return

        # ── Passengers ────────────────────────────────────────────────────────
        passengers = []
        for i in range(1, 6):
            email = f'passenger{i}@testpassenger.dev'
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': f'Passenger',
                    'last_name': f'{i}',
                    'role': 'user',
                    'is_active': True,
                },
            )
            if created:
                user.set_password('testpass123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Passenger: {email}'))
            passengers.append(user)

        # ── Drivers ───────────────────────────────────────────────────────────
        drivers_data = [
            {
                'email': 'driver1@testdriver.dev',
                'first_name': 'Іван',
                'last_name': 'Коваль',
                'vehicle_make': 'Toyota',
                'vehicle_model': 'Camry',
                'vehicle_year': 2021,
                'vehicle_color': 'Білий',
                'vehicle_plate': 'AA1234BB',
                'vehicle_type': Driver.VehicleType.COMFORT,
                'license_number': 'DRV-001',
            },
            {
                'email': 'driver2@testdriver.dev',
                'first_name': 'Олег',
                'last_name': 'Мельник',
                'vehicle_make': 'Volkswagen',
                'vehicle_model': 'Passat',
                'vehicle_year': 2020,
                'vehicle_color': 'Чорний',
                'vehicle_plate': 'BB5678CC',
                'vehicle_type': Driver.VehicleType.ECONOMY,
                'license_number': 'DRV-002',
            },
        ]

        created_drivers = []
        for dd in drivers_data:
            email = dd.pop('email')
            first_name = dd.pop('first_name')
            last_name = dd.pop('last_name')

            user, u_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': 'driver',
                    'is_active': True,
                    'is_verified': True,
                },
            )
            if u_created:
                user.set_password('testpass123')
                user.save()

            driver, d_created = Driver.objects.get_or_create(
                user=user,
                defaults={
                    'status': Driver.Status.APPROVED,
                    'availability': Driver.Availability.ONLINE,
                    'current_location': Point(30.5, 50.45, srid=4326),
                    **dd,
                },
            )
            if d_created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Driver: {email}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ! Driver exists: {email}'))

            created_drivers.append(driver)

        # ── Rides (last 3 months) ─────────────────────────────────────────────
        now = timezone.now()
        pickup = Point(30.523, 50.450, srid=4326)
        dropoff = Point(30.600, 50.480, srid=4326)

        total_created = 0
        for driver in created_drivers:
            existing = Ride.objects.filter(driver=driver).count()
            if existing >= rides_count:
                self.stdout.write(self.style.WARNING(f'  ! Rides exist for {driver.user.email}, skipping'))
                continue

            ride_rating_sum = 0.0
            ride_rating_count = 0

            for i in range(rides_count):
                days_ago = random.randint(0, 89)
                hours_ago = random.randint(0, 23)
                created_at = now - timedelta(days=days_ago, hours=hours_ago)
                accepted_at = created_at + timedelta(seconds=random.randint(30, 300))
                started_at = accepted_at + timedelta(minutes=random.randint(2, 8))
                completed_at = started_at + timedelta(minutes=random.randint(10, 45))
                ride_rating = random.randint(3, 5)
                passenger = random.choice(passengers)

                ride = Ride.objects.create(
                    user=passenger,
                    driver=driver,
                    status=Ride.Status.COMPLETED,
                    vehicle_type=driver.vehicle_type,
                    pickup_location=pickup,
                    dropoff_location=dropoff,
                    pickup_address='вул. Хрещатик, 1, Київ',
                    dropoff_address='вул. Велика Васильківська, 55, Київ',
                    estimated_distance=7.5,
                    estimated_duration=20,
                    estimated_price=120,
                    final_distance=7.8,
                    final_duration=22,
                    final_price=125,
                    rating=ride_rating,
                    created_at=created_at,
                    accepted_at=accepted_at,
                    started_at=started_at,
                    completed_at=completed_at,
                )

                # Create payment with random cash/card split (~60% cash, 40% card)
                payment_method = random.choices(
                    ['cash', 'card'],
                    weights=[60, 40],
                )[0]
                Payment.objects.create(
                    ride=ride,
                    user=passenger,
                    amount=125,
                    currency='UAH',
                    status='success',
                    payment_method=payment_method,
                    provider='cash' if payment_method == 'cash' else 'liqpay',
                    provider_transaction_id=f'test_{ride.id}',
                    processed_at=completed_at,
                )

                ride_rating_sum += ride_rating
                ride_rating_count += 1
                total_created += 1

            # Update driver aggregate fields
            if ride_rating_count > 0:
                from django.db.models import Sum
                from apps.payments.models import Payment as P
                driver.rating = round(ride_rating_sum / ride_rating_count, 2)
                driver.total_rides = Ride.objects.filter(
                    driver=driver, status=Ride.Status.COMPLETED
                ).count()
                driver.total_earnings = Ride.objects.filter(
                    driver=driver, status=Ride.Status.COMPLETED
                ).aggregate(total=Sum('final_price'))['total'] or 0

                cash_total = P.objects.filter(
                    ride__driver=driver, status='success', payment_method='cash'
                ).aggregate(total=Sum('amount'))['total'] or 0
                card_total = P.objects.filter(
                    ride__driver=driver, status='success', payment_method='card'
                ).aggregate(total=Sum('amount'))['total'] or 0

                driver.cash_earnings = cash_total
                driver.card_earnings = card_total
                driver.pending_card_withdrawal = card_total
                driver.save(update_fields=[
                    'rating', 'total_rides', 'total_earnings',
                    'cash_earnings', 'card_earnings', 'pending_card_withdrawal',
                ])

            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ {rides_count} rides for {driver.user.email} '
                    f'| rating={driver.rating} total={driver.total_rides} '
                    f'| cash={driver.cash_earnings} card={driver.card_earnings}'
                )
            )

        self.stdout.write(self.style.SUCCESS(f'\n✓ Done! Created {total_created} rides.'))