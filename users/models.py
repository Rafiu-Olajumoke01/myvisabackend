from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User Model
    """
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.email or self.username

    @property
    def fullname(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username