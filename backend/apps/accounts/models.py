import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"  # everything, including settings and staff
    MANAGER = "MANAGER", "Manager"  # operations + finance (verify payments, documents, reports)
    STAFF = "STAFF", "Staff"  # day-to-day booking operations, read-only finance


class AdminUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role=Role.ADMIN)
        return self._create_user(email, password, **extra)


class AdminUser(AbstractBaseUser, PermissionsMixin):
    """Staff member. Guests never have accounts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=120)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    dashboard_access = models.BooleanField(default=True, help_text="Allow sign-in to the management dashboard.")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text="Allow access to the Django admin site.")
    date_joined = models.DateTimeField(default=timezone.now)

    objects = AdminUserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "admin user"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    def has_role(self, *roles) -> bool:
        return self.is_active and (self.is_superuser or self.role in roles)
