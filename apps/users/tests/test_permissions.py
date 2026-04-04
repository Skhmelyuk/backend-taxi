import pytest
from unittest.mock import MagicMock
from rest_framework.test import APIRequestFactory
from core.permissions import IsAdminUser, IsDriverUser, IsOwnerOrAdmin, IsOwnerOrReadOnly
from apps.users.tests.factories import UserFactory, AdminUserFactory, DriverUserFactory


@pytest.mark.django_db
class TestIsAdminUser:

    def test_admin_has_permission(self):
        admin = AdminUserFactory()
        request = MagicMock()
        request.user = admin
        perm = IsAdminUser()
        assert perm.has_permission(request, None) is True

    def test_regular_user_no_permission(self):
        user = UserFactory()
        request = MagicMock()
        request.user = user
        perm = IsAdminUser()
        assert perm.has_permission(request, None) is False

    def test_driver_no_permission(self):
        driver = DriverUserFactory()
        request = MagicMock()
        request.user = driver
        perm = IsAdminUser()
        assert perm.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsDriverUser:

    def test_driver_has_permission(self):
        driver = DriverUserFactory()
        request = MagicMock()
        request.user = driver
        perm = IsDriverUser()
        assert perm.has_permission(request, None) is True

    def test_regular_user_no_permission(self):
        user = UserFactory()
        request = MagicMock()
        request.user = user
        perm = IsDriverUser()
        assert perm.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsOwnerOrAdmin:

    def test_owner_has_permission(self):
        user = UserFactory()
        request = MagicMock()
        request.user = user
        perm = IsOwnerOrAdmin()
        assert perm.has_object_permission(request, None, user) is True

    def test_admin_has_permission(self):
        admin = AdminUserFactory()
        other_user = UserFactory()
        request = MagicMock()
        request.user = admin
        perm = IsOwnerOrAdmin()
        assert perm.has_object_permission(request, None, other_user) is True

    def test_other_user_no_permission(self):
        user1 = UserFactory()
        user2 = UserFactory()
        request = MagicMock()
        request.user = user1
        perm = IsOwnerOrAdmin()
        assert perm.has_object_permission(request, None, user2) is False
