"""
User models.
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user.
        
        Args:
            email: User email
            password: User password (optional for Clerk users)
            **extra_fields: Additional fields
            
        Returns:
            Created User instance
        """
        if not email:
            raise ValueError('Email is required')

        email = self.normalize_email(email)
        
        # Default to passenger if no role specified
        extra_fields.setdefault('is_passenger', True)
        
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser.
        
        Args:
            email: User email
            password: User password
            **extra_fields: Additional fields
            
        Returns:
            Created superuser instance
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_passenger', True)
        extra_fields.setdefault('is_driver', False)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model.
    
    Користувач може бути одночасно пасажиром і водієм.
    is_passenger - доступ до client-app
    is_driver - доступ до driver-app  
    is_staff - доступ до admin панелі
    """

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Clerk integration
    clerk_user_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True, db_index=True,
        verbose_name='Clerk ID',
    )

    email = models.EmailField(
        unique=True, db_index=True,
        verbose_name='Email',
    )
    phone_number = models.CharField(
        max_length=20, unique=True, null=True, blank=True,
        verbose_name='Телефон',
    )
    first_name = models.CharField(
        max_length=100, blank=True,
        verbose_name="Ім'я",
    )
    last_name = models.CharField(
        max_length=100, blank=True,
        verbose_name='Прізвище',
    )
    profile_image = models.URLField(
        max_length=500, blank=True,
        verbose_name='Фото',
    )
    date_of_birth = models.DateField(
        null=True, blank=True,
        verbose_name='Дата народження',
    )

    # Ролі користувача (можуть бути обидві True)
    is_passenger = models.BooleanField(
        default=True,
        verbose_name='Пасажир',
        help_text='Має доступ до client-app'
    )
    is_driver = models.BooleanField(
        default=False,
        verbose_name='Водій',
        help_text='Має доступ до driver-app'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Адміністратор',
        help_text='Доступ до admin панелі'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Активний',
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Підтверджений',
    )

    # Push notifications
    fcm_token = models.TextField(blank=True, verbose_name='FCM Token')

    # Statistics
    total_rides = models.PositiveIntegerField(default=0, verbose_name='Всього поїздок')
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Всього витрачено')
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='Середній рейтинг')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    updated_at = models.DateTimeField(auto_now=True,       verbose_name='Оновлено')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='Останній вхід')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['clerk_user_id']),
            models.Index(fields=['is_passenger']),
            models.Index(fields=['is_driver']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'

    def __str__(self) -> str:
        """String representation."""
        return self.email

    @property
    def full_name(self) -> str:
        """
        Return full name.
        
        Returns:
            Full name or email if name not set
        """
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.email

    def get_short_name(self) -> str:
        """
        Return short name.
        
        Returns:
            First name or email
        """
        return self.first_name if self.first_name else self.email

    @property
    def role_display(self) -> str:
        """Return display string for user roles."""
        roles = []
        if self.is_passenger:
            roles.append('Пасажир')
        if self.is_driver:
            roles.append('Водій')
        if self.is_staff:
            roles.append('Адмін')
        return ', '.join(roles) if roles else 'Користувач'

    def can_become_driver(self) -> bool:
        """Check if user can register as driver."""
        return not self.is_driver

    def can_become_passenger(self) -> bool:
        """Check if user can use client app."""
        return True

    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])