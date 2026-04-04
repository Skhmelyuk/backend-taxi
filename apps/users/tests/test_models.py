import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:

    def test_create_user(self):
        user = User.objects.create_user(email='test@example.com', password='testpass123')
        assert user.email == 'test@example.com'
        assert user.role == User.Role.USER
        assert user.is_active is True
        assert user.is_staff is False
        assert user.check_password('testpass123')

    def test_create_user_no_password(self):
        user = User.objects.create_user(email='nopass@example.com')
        assert not user.has_usable_password()

    def test_create_user_without_email(self):
        with pytest.raises(ValueError, match='Email is required'):
            User.objects.create_user(email='', password='testpass123')

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email='admin@example.com', password='adminpass123')
        assert admin.role == User.Role.ADMIN
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_create_superuser_not_staff(self):
        with pytest.raises(ValueError, match='Superuser must have is_staff=True'):
            User.objects.create_superuser(email='admin@example.com', password='password', is_staff=False)

    def test_create_superuser_not_superuser(self):
        with pytest.raises(ValueError, match='Superuser must have is_superuser=True'):
            User.objects.create_superuser(email='admin@example.com', password='password', is_superuser=False)

    def test_user_full_name(self):
        user = User.objects.create_user(
            email='test@example.com', first_name='John', last_name='Doe'
        )
        assert user.full_name == 'John Doe'

    def test_user_full_name_empty(self):
        user = User.objects.create_user(email='test@example.com')
        assert user.full_name == 'test@example.com'

    def test_user_full_name_only_first_name(self):
        user = User.objects.create_user(email='test@example.com', first_name='John')
        assert user.full_name == 'John'

    def test_user_str(self):
        user = User.objects.create_user(email='test@example.com')
        assert str(user) == 'test@example.com'

    def test_update_last_login(self):
        user = User.objects.create_user(email='test@example.com')
        assert user.last_login is None
        user.update_last_login()
        assert user.last_login is not None