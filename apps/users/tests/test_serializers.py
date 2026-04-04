import pytest
from apps.users.models import User
from apps.users.tests.factories import UserFactory
from apps.users.serializers import (
    UserSerializer, UserDetailSerializer, UserUpdateSerializer,
    FCMTokenSerializer, UserListSerializer,
)


@pytest.mark.django_db
class TestUserSerializer:

    def test_serialize_user(self):
        user = UserFactory(first_name='John', last_name='Doe')
        data = UserSerializer(user).data
        assert data['email'] == user.email
        assert data['full_name'] == 'John Doe'
        assert data['role'] == 'user'

    def test_read_only_fields_not_updated(self):
        user = UserFactory()
        serializer = UserSerializer(user, data={'email': 'new@test.com', 'role': 'admin'})
        assert serializer.is_valid()
        serializer.save()
        user.refresh_from_db()
        assert user.email != 'new@test.com'
        assert user.role == 'user'


@pytest.mark.django_db
class TestUserUpdateSerializer:

    def test_update_profile(self):
        user = UserFactory()
        serializer = UserUpdateSerializer(user, data={
            'first_name': 'Jane', 'last_name': 'Smith', 'phone_number': '+380501234567'
        })
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.first_name == 'Jane'
        assert updated.phone_number == '+380501234567'

    def test_invalid_phone(self):
        user = UserFactory()
        serializer = UserUpdateSerializer(user, data={'phone_number': 'invalid'})
        assert not serializer.is_valid()
        assert 'phone_number' in serializer.errors

    def test_partial_update(self):
        user = UserFactory(first_name='John', last_name='Doe')
        serializer = UserUpdateSerializer(user, data={'first_name': 'Jane'}, partial=True)
        assert serializer.is_valid()
        updated = serializer.save()
        assert updated.first_name == 'Jane'
        assert updated.last_name == 'Doe'


@pytest.mark.django_db
class TestFCMTokenSerializer:

    def test_valid_token(self):
        serializer = FCMTokenSerializer(data={'fcm_token': 'valid_fcm_token_abc123'})
        assert serializer.is_valid()

    def test_invalid_short_token(self):
        serializer = FCMTokenSerializer(data={'fcm_token': 'short'})
        assert not serializer.is_valid()

    def test_missing_token(self):
        serializer = FCMTokenSerializer(data={})
        assert not serializer.is_valid()