import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestCustomExceptionHandler:
    """Tests for custom exception handler."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        client = APIClient()
        response = client.get('/api/v1/health/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'healthy'
        assert 'timestamp' in response.data