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
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model."""

    class Role(models.TextChoices):
        USER = 'user', 'User'
        DRIVER = 'driver', 'Driver'
        ADMIN = 'admin', 'Admin'

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Clerk integration
    clerk_user_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='Clerk user ID for authentication'
    )

    # Basic info
    email = models.EmailField(
        unique=True,
        db_index=True,
        help_text='User email address'
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text='User phone number in international format'
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='User first name'
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='User last name'
    )
    profile_image = models.URLField(
        max_length=500,
        blank=True,
        help_text='URL to user profile image'
    )

    # Role and permissions
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
        help_text='User role in the system'
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this user should be treated as active'
    )
    is_staff = models.BooleanField(
        default=False,
        help_text='Designates whether the user can log into admin site'
    )
    is_verified = models.BooleanField(
        default=False,
        help_text='Designates whether the user has verified their email/phone'
    )

    # Push notifications
    fcm_token = models.TextField(
        blank=True,
        help_text='Firebase Cloud Messaging token for push notifications'
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Date and time when user was created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Date and time when user was last updated'
    )
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date and time of last login'
    )

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
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'User'
        verbose_name_plural = 'Users'

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

    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])