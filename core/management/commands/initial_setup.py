"""
Management command for initial project setup.

Complete setup
python manage.py initial_setup

Only migrations
python manage.py initial_setup --skip-superuser

No migrations
python manage.py initial_setup --skip-migrations
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.management import call_command

User = get_user_model()

class Command(BaseCommand):
    help = 'Initial project setup: migrations, superuser, etc.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip running migrations',
        )
        parser.add_argument(
            '--skip-superuser',
            action='store_true',
            help='Skip creating superuser',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting initial setup...'))
        
        # Check database connection
        self.stdout.write('Checking database connection...')
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS('✓ Database connected'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database connection failed: {e}'))
            return
        
        # Run migrations
        if not options['skip_migrations']:
            self.stdout.write('Running migrations...')
            try:
                call_command('migrate', interactive=False)
                self.stdout.write(self.style.SUCCESS('✓ Migrations applied'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Migrations failed: {e}'))
                return
        
        # Create superuser
        if not options['skip_superuser']:
            self.stdout.write('Creating superuser...')
            try:
                if not User.objects.filter(username='admin').exists():
                    User.objects.create_superuser(
                        username='admin',
                        email='admin@example.com',
                        password='admin123'
                    )
                    self.stdout.write(self.style.SUCCESS('✓ Superuser created (username: admin, password: admin123)'))
                else:
                    self.stdout.write(self.style.WARNING('! Superuser already exists'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Superuser creation failed: {e}'))
        
        # Collect static files
        self.stdout.write('Collecting static files...')
        try:
            call_command('collectstatic', interactive=False, clear=True)
            self.stdout.write(self.style.SUCCESS('✓ Static files collected'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'! Static files collection failed: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Initial setup completed!'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Run: python manage.py runserver')
        self.stdout.write('2. Open: http://localhost:8000/admin/')
        self.stdout.write('3. Login with: admin / admin123')