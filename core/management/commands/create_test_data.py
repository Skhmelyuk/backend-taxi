"""
Management command to create test data.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test data for development'

    def handle(self, *args, **options):
        self.stdout.write('Creating test data...')
        
        # Create test users
        test_users = [
            {'username': 'user1', 'email': 'user1@example.com', 'password': 'password123'},
            {'username': 'user2', 'email': 'user2@example.com', 'password': 'password123'},
            {'username': 'driver1', 'email': 'driver1@example.com', 'password': 'password123'},
        ]
        
        for user_data in test_users:
            if not User.objects.filter(username=user_data['username']).exists():
                User.objects.create_user(**user_data)
                self.stdout.write(self.style.SUCCESS(f"✓ Created user: {user_data['username']}"))
            else:
                self.stdout.write(self.style.WARNING(f"! User exists: {user_data['username']}"))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Test data created!'))