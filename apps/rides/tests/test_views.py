import uuid
import pytest
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.drivers.models import Driver
from apps.rides.models import Ride


@pytest.mark.django_db
class TestRideViewSet(TestCase):
    """Testing RideViewSet"""
    def setUp(self):
        self.client = APIClient()
        
        # Create user
        self.user = User.objects.create_user(
            email='user@example.com',
            password='password123',
            role='user'
        )
        
        # Create driver
        self.driver_user = User.objects.create_user(
            email='driver@example.com',
            password='password123',
            role='driver'
        )
        self.driver_profile = Driver.objects.create(
            user=self.driver_user,
            status='approved',
            availability='online',
            vehicle_type='economy',
            vehicle_make='Toyota',
            vehicle_model='Prius',
            vehicle_year=2020,
            vehicle_color='White',
            vehicle_plate='AB1234CD',
            license_number='LIC12345',
            license_expiry='2028-01-01'
        )
        
        # Create admin
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password123'
        )
        
        # Create rides for queryset tests
        self.ride_user = Ride.objects.create(
            user=self.user,
            vehicle_type='economy',
            pickup_location=Point(30.0, 50.0),
            dropoff_location=Point(30.1, 50.1),
            pickup_address='Pickup A',
            dropoff_address='Dropoff A',
            estimated_distance=5.0,
            estimated_duration=10,
            estimated_price=150.0
        )
        
        self.ride_driver = Ride.objects.create(
            user=self.user,
            driver=self.driver_profile,
            status=Ride.Status.ACCEPTED,
            vehicle_type='economy',
            pickup_location=Point(30.0, 50.0),
            dropoff_location=Point(30.1, 50.1),
            pickup_address='Pickup B',
            dropoff_address='Dropoff B',
            estimated_distance=5.0,
            estimated_duration=10,
            estimated_price=150.0
        )

    def test_get_queryset_user(self):
        """Testing get_queryset for user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_get_queryset_driver(self):
        """Testing get_queryset for driver"""
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Driver should only see rides assigned to them
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.ride_driver.id))

    def test_get_queryset_admin(self):
        """Testing get_queryset for admin"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin sees all rides
        self.assertEqual(len(response.data['results']), 2)

    @patch('apps.rides.views.RideService.create_ride')
    def test_create_ride_success(self, mock_create):
        """Testing create_ride success"""
        mock_create.return_value = self.ride_user
        
        self.client.force_authenticate(user=self.user)
        data = {
            'pickup_lat': 50.0,
            'pickup_lon': 30.0,
            'dropoff_lat': 50.1,
            'dropoff_lon': 30.1,
            'pickup_address': 'Address A',
            'dropoff_address': 'Address B',
            'vehicle_type': 'economy'
        }
        response = self.client.post(reverse('ride-create-ride'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['id'], str(self.ride_user.id))
        mock_create.assert_called_once()

    @patch('apps.rides.views.RideService.create_ride')
    def test_create_ride_failure_validation(self, mock_create):
        """Testing create_ride failure validation"""
        self.client.force_authenticate(user=self.user)
        data = {
            # Missing fields
            'pickup_lat': 50.0,
        }
        response = self.client.post(reverse('ride-create-ride'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_create.assert_not_called()

    @patch('apps.rides.views.RideService.create_ride')
    def test_create_ride_service_error(self, mock_create):
        """Testing create_ride service error"""
        mock_create.side_effect = ValueError("No drivers available")
        
        self.client.force_authenticate(user=self.user)
        data = {
            'pickup_lat': 50.0,
            'pickup_lon': 30.0,
            'dropoff_lat': 50.1,
            'dropoff_lon': 30.1,
            'pickup_address': 'Address A',
            'dropoff_address': 'Address B',
            'vehicle_type': 'economy'
        }
        response = self.client.post(reverse('ride-create-ride'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "No drivers available")

    @patch('apps.rides.views.PricingService.get_price_estimate')
    def test_estimate_success(self, mock_estimate):
        """Testing estimate success"""
        mock_estimate.return_value = {
            'price': 150.0,
            'distance_km': 5.0,
            'duration_min': 10
        }
        
        self.client.force_authenticate(user=self.user)
        data = {
            'pickup_lat': 50.0,
            'pickup_lon': 30.0,
            'dropoff_lat': 50.1,
            'dropoff_lon': 30.1,
            'vehicle_type': 'economy'
        }
        response = self.client.post(reverse('ride-estimate'), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('economy', response.data['estimates'])
        self.assertIn('comfort', response.data['estimates'])
        self.assertIn('business', response.data['estimates'])
        self.assertEqual(mock_estimate.call_count, 3)

    @patch('apps.rides.views.RideService.accept_ride')
    def test_accept_ride_driver_success(self, mock_accept):
        """Testing accept_ride driver success"""
        mock_accept.return_value = self.ride_driver
        
        self.client.force_authenticate(user=self.driver_user)
        url = reverse('ride-accept', kwargs={'pk': self.ride_driver.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.ride_driver.id))
        mock_accept.assert_called_once()
        
    def test_accept_ride_user_forbidden(self):
        """Testing accept_ride user forbidden"""
        self.client.force_authenticate(user=self.user)
        url = reverse('ride-accept', kwargs={'pk': self.ride_user.id})
        response = self.client.post(url)
        # Users aren't drivers
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('apps.rides.views.RideService.start_ride')
    def test_start_ride_success(self, mock_start):
        """Testing start_ride success"""
        mock_start.return_value = self.ride_driver
        
        self.client.force_authenticate(user=self.driver_user)
        url = reverse('ride-start', kwargs={'pk': self.ride_driver.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_start.assert_called_once()

    @patch('apps.rides.views.RideService.complete_ride')
    def test_complete_ride_success(self, mock_complete):
        """Testing complete_ride success"""
        mock_complete.return_value = self.ride_driver
        
        self.client.force_authenticate(user=self.driver_user)
        url = reverse('ride-complete', kwargs={'pk': self.ride_driver.id})
        response = self.client.post(url, {'actual_distance_km': 6.5})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_complete.assert_called_once()

    @patch('apps.rides.views.RideService.cancel_ride')
    def test_cancel_ride_success(self, mock_cancel):
        """Testing cancel_ride success"""
        mock_cancel.return_value = self.ride_user
        
        self.client.force_authenticate(user=self.user)
        url = reverse('ride-cancel', kwargs={'pk': self.ride_user.id})
        data = {
            'reason': 'user_cancelled',
            'comment': 'Changed my mind'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_cancel.assert_called_once()

    @patch('apps.rides.views.RideService.rate_ride')
    def test_rate_ride_success(self, mock_rate):
        """Testing rate_ride success"""
        mock_rate.return_value = self.ride_user
        
        self.client.force_authenticate(user=self.user)
        url = reverse('ride-rate', kwargs={'pk': self.ride_user.id})
        data = {
            'rating': 5,
            'comment': 'Great driver!'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_rate.assert_called_once()