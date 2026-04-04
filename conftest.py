"""
Pytest configuration and global fixtures.
"""

import pytest
from typing import Tuple, Any
from rest_framework.test import APIClient
from apps.users.models import User

@pytest.fixture
def api_client() -> APIClient:
    """
    Return a clean instance of DRF APIClient.
    
    Returns:
        APIClient: The Django REST Framework test client.
    """
    return APIClient()


@pytest.fixture
def user_factory(db: Any) -> Any:
    """
    Fixture providing access to UserFactory.
    
    Returns:
        UserFactory: The factory class for generating standard users.
    """
    from apps.users.tests.factories import UserFactory
    return UserFactory


@pytest.fixture
def admin_factory(db: Any) -> Any:
    """
    Fixture providing access to AdminUserFactory.
    
    Returns:
        AdminUserFactory: The factory class for generating admin users.
    """
    from apps.users.tests.factories import AdminUserFactory
    return AdminUserFactory


@pytest.fixture
def driver_factory(db: Any) -> Any:
    """
    Fixture providing access to DriverUserFactory.
    
    Returns:
        DriverUserFactory: The factory class for generating driver users.
    """
    from apps.users.tests.factories import DriverUserFactory
    return DriverUserFactory


@pytest.fixture
def user(db: Any) -> User:
    """
    Create and return a standard test user.
    
    Returns:
        User: A persisted User instance with 'user' role.
    """
    from apps.users.tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def admin(db: Any) -> User:
    """
    Create and return an admin test user.
    
    Returns:
        User: A persisted User instance with 'admin' role.
    """
    from apps.users.tests.factories import AdminUserFactory
    return AdminUserFactory()


@pytest.fixture
def driver(db: Any) -> User:
    """
    Create and return a driver test user.
    
    Returns:
        User: A persisted User instance with 'driver' role.
    """
    from apps.users.tests.factories import DriverUserFactory
    return DriverUserFactory()


@pytest.fixture
def authenticated_client(api_client: APIClient, user: User) -> Tuple[APIClient, User]:
    """
    Return an API client authenticated as a regular user.
    
    Returns:
        tuple: (APIClient, User)
    """
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def admin_client(api_client: APIClient, admin: User) -> Tuple[APIClient, User]:
    """
    Return an API client authenticated as an admin.
    
    Returns:
        tuple: (APIClient, User)
    """
    api_client.force_authenticate(user=admin)
    return api_client, admin


@pytest.fixture
def driver_client(api_client: APIClient, driver: User) -> Tuple[APIClient, User]:
    """
    Return an API client authenticated as a driver.
    
    Returns:
        tuple: (APIClient, User)
    """
    api_client.force_authenticate(user=driver)
    return api_client, driver