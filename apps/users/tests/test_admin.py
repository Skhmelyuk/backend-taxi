import pytest
from django.test import Client
from django.urls import reverse
from apps.users.tests.factories import UserFactory, AdminUserFactory


@pytest.mark.django_db
class TestUserAdmin:

    def test_admin_list_accessible(self):
        admin = AdminUserFactory(password='adminpass')
        client = Client()
        client.force_login(admin)
        url = reverse('admin:users_user_changelist')
        response = client.get(url)
        assert response.status_code == 200

    def test_admin_detail_accessible(self):
        admin = AdminUserFactory(password='adminpass')
        user = UserFactory()
        client = Client()
        client.force_login(admin)
        url = reverse('admin:users_user_change', args=[user.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_non_admin_cannot_access(self):
        user = UserFactory()
        client = Client()
        client.force_login(user)
        url = reverse('admin:users_user_changelist')
        response = client.get(url)
        assert response.status_code == 302
