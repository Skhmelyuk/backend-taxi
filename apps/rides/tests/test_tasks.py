import pytest
from apps.rides.tasks import cancel_timeout_rides, generate_daily_ride_report


@pytest.mark.django_db
class TestRideCeleryTasks:
    """Tests for Celery tasks related to rides."""
    def test_cancel_timeout_no_pending(self):
        """Test that no rides are cancelled if there are no pending rides."""
        result = cancel_timeout_rides.apply()
        assert result.result['cancelled'] == 0

    def test_cancel_timeout_with_old_ride(self):
        """Test that pending rides older than 10 minutes are cancelled."""
        from decimal import Decimal
        from django.contrib.gis.geos import Point
        from django.utils import timezone
        from datetime import timedelta
        from apps.rides.models import Ride
        from apps.users.tests.factories import UserFactory

        user = UserFactory()
        ride = Ride.objects.create(
            user=user, vehicle_type='economy',
            pickup_location=Point(30.5234, 50.4501, srid=4326),
            dropoff_location=Point(30.6234, 50.4601, srid=4326),
            pickup_address='A', dropoff_address='B',
            estimated_distance=Decimal('5.0'),
            estimated_duration=20,
            estimated_price=Decimal('80.0'),
            status='pending',
        )
        # Simulate old ride
        Ride.objects.filter(id=ride.id).update(
            created_at=timezone.now() - timedelta(minutes=15)
        )
        result = cancel_timeout_rides.apply()
        assert result.result['cancelled'] == 1

    def test_generate_daily_report(self):
        """Test that the daily ride report task runs without errors."""
        result = generate_daily_ride_report.apply()
        assert 'total_rides' in result.result
        assert 'total_revenue' in result.result

    def test_find_driver_for_ride_not_pending(self):
        """Test find_driver_for_ride on non-pending ride."""
        from apps.rides.tasks import find_driver_for_ride
        from apps.rides.tests.factories import RideFactory
        ride = RideFactory(status='accepted')
        result = find_driver_for_ride.apply(args=[str(ride.id)])
        assert result.result is None

    def test_find_driver_for_ride_success(self):
        """Test find_driver_for_ride when match is found."""
        from apps.rides.tasks import find_driver_for_ride
        from apps.rides.tests.factories import RideFactory
        from apps.drivers.tests.factories import DriverFactory
        from unittest.mock import patch

        ride = RideFactory(status='pending')
        driver = DriverFactory()

        with patch('apps.rides.services.matching_service.MatchingService.auto_match_ride', return_value=driver):
            result = find_driver_for_ride.apply(args=[str(ride.id)])
            assert result.result == {'matched': True, 'driver_id': str(driver.id)}

    def test_find_driver_for_ride_retry(self):
        """Test find_driver_for_ride retries when no driver found."""
        from apps.rides.tasks import find_driver_for_ride
        from apps.rides.tests.factories import RideFactory
        from unittest.mock import patch

        ride = RideFactory(status='pending')

        with patch('apps.rides.services.matching_service.MatchingService.auto_match_ride', return_value=None):
            with patch('celery.app.task.Task.retry') as mock_retry:
                mock_retry.side_effect = Exception('RetryException')
                with pytest.raises(Exception, match='RetryException'):
                    find_driver_for_ride(str(ride.id))

    def test_find_driver_for_ride_max_retries(self):
        """Test find_driver_for_ride max retries aborts and cancels ride."""
        from apps.rides.tasks import find_driver_for_ride
        from apps.rides.tests.factories import RideFactory
        from unittest.mock import patch, PropertyMock

        ride = RideFactory(status='pending')

        # Mock the entire task function internals
        with patch('apps.rides.services.matching_service.MatchingService.auto_match_ride', return_value=None):
            with patch('celery.app.task.Task.retry', side_effect=Exception("Task Retry")):
                with patch('celery.app.task.Task.request', new_callable=PropertyMock) as mock_request:
                    mock_request.return_value.retries = 3
                    
                    try:
                        # Direct call bypasses Celery machinery but we set max_retries
                        old_max = find_driver_for_ride.max_retries
                        find_driver_for_ride.max_retries = 3
                        result = find_driver_for_ride(str(ride.id))
                        assert result == {'matched': False}
                        ride.refresh_from_db()
                        assert ride.status == 'cancelled'
                        assert ride.cancellation_reason == 'no_drivers'
                    finally:
                        find_driver_for_ride.max_retries = old_max

    def test_find_driver_for_ride_max_retries_ride_not_found(self):
        """Test inner exception pass when ride doesn't exist during max retries cancel."""
        from apps.rides.tasks import find_driver_for_ride
        from unittest.mock import patch, PropertyMock
        
        with patch('apps.rides.models.Ride.objects.get', side_effect=Exception("Task Retry")):
            with patch('celery.app.task.Task.request', new_callable=PropertyMock) as mock_request:
                mock_request.return_value.retries = 3
                try:
                    old_max = find_driver_for_ride.max_retries
                    find_driver_for_ride.max_retries = 3
                    result = find_driver_for_ride('nonexistent-id')
                    assert result == {'matched': False}
                finally:
                    find_driver_for_ride.max_retries = old_max

    def test_calculate_ride_statistics_not_completed(self):
        """Test calculate_ride_statistics on non-completed ride."""
        from apps.rides.tasks import calculate_ride_statistics
        from apps.rides.tests.factories import RideFactory
        ride = RideFactory(status='pending')
        result = calculate_ride_statistics.apply(args=[str(ride.id)])
        assert result.result is None

    def test_calculate_ride_statistics_success(self):
        """Test calculate_ride_statistics on completed ride."""
        from apps.rides.tasks import calculate_ride_statistics
        from apps.rides.tests.factories import RideFactory
        ride = RideFactory(status='completed')
        result = calculate_ride_statistics.apply(args=[str(ride.id)])
        assert result.result == {'ride_id': str(ride.id), 'status': 'ok'}

    def test_calculate_ride_statistics_exception(self):
        """Test calculate_ride_statistics handles exceptions gracefully."""
        from apps.rides.tasks import calculate_ride_statistics
        from unittest.mock import patch
        
        with patch('apps.rides.models.Ride.objects.get', side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                calculate_ride_statistics('fake-id')