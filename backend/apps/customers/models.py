from django.db import models
from django.db.models.functions import Lower

from apps.core.models import TimeStampedModel, UUIDModel


class Customer(UUIDModel, TimeStampedModel):
    """A guest who has made at least one booking. No password, no account."""

    full_name = models.CharField(max_length=120)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=40)
    nationality = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(Lower("email"), name="customer_email_ci_unique")]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
