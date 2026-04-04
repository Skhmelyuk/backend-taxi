import pytest
from unittest.mock import patch, MagicMock
from celery.exceptions import Retry
from apps.drivers.tasks import (
    cleanup_stale_locations, 
    update_driver_statistics,
    notify_driver_new_ride,
    check_driver_documents_expiry
)

@pytest.mark.django_db
class TestDriverCeleryTasks:

    def test_cleanup_stale_locations_no_stale(self):
        # No stale drivers — should return 0
        result = cleanup_stale_locations.apply()
        assert result.result['cleaned'] == 0

    @patch('apps.drivers.models.Driver.objects')
        # There is information about one outdated driver
    def test_cleanup_stale_locations_with_stale(self, mock_objects):
        mock_driver = MagicMock()
        mock_objects.filter.return_value = [mock_driver]
        result = cleanup_stale_locations.apply()
        assert result.successful()

    @patch('apps.drivers.models.Driver.objects')
    @patch('apps.drivers.tasks.cleanup_stale_locations.retry')
    def test_cleanup_stale_locations_exception_and_retry(self, mock_retry, mock_objects):
        # Simulate an exception in the database
        mock_objects.filter.side_effect = Exception("Database error")
        # Simulating the behavior of self.retry()
        mock_retry.side_effect = Retry("Retry called")
        
        # The apply() call should catch Retry (if Celery doesn't swallow, 
        # or we can check the exception directly)
        with pytest.raises(Retry):
            cleanup_stale_locations()
            
        mock_retry.assert_called_once()

    @pytest.mark.django_db
        # Test updating driver statistics with an invalid driver ID
    def test_update_driver_statistics_invalid_id(self):
        result = update_driver_statistics.apply(args=['invalid-uuid'])
        assert result.failed()

    @patch('apps.drivers.models.Driver.objects')
        # Test updating driver statistics with a valid driver ID
    def test_update_driver_statistics_success(self, mock_objects):
        mock_driver = MagicMock()
        mock_driver.user.email = "driver@test.com"
        mock_objects.get.return_value = mock_driver
        
        result = update_driver_statistics.apply(args=['valid-uuid'])
        assert result.successful()
        assert result.result['status'] == 'updated'
        assert result.result['driver_id'] == 'valid-uuid'

    @patch('apps.drivers.models.Driver.objects')
        # Test notifying driver about a new ride with a valid driver ID
    def test_notify_driver_new_ride_success(self, mock_objects):
        mock_driver = MagicMock()
        mock_driver.user.email = "notify@test.com"
        mock_objects.get.return_value = mock_driver
        
        result = notify_driver_new_ride.apply(args=['driver-id', 'ride-id'])
        assert result.successful()
        assert result.result['notified'] is True
        assert result.result['ride_id'] == 'ride-id'

    @patch('apps.drivers.models.Driver.objects')
        # Test notifying driver about a new ride with an invalid driver ID
    def test_notify_driver_new_ride_exception(self, mock_objects):
        mock_objects.get.side_effect = Exception("Driver not found")
        result = notify_driver_new_ride.apply(args=['invalid-driver', 'ride-id'])
        assert result.failed()

    @patch('apps.drivers.models.Driver.objects')
        # Test checking driver documents expiry with some expiring drivers
    def test_check_driver_documents_expiry(self, mock_objects):
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5
        mock_objects.filter.return_value = mock_qs
        
        result = check_driver_documents_expiry.apply()
        assert result.successful()
        assert result.result['expiring_count'] == 5