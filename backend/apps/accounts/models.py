from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.accounts.managers import UserManager


class User(AbstractUser):
    """Custom user identified by e-mail rather than username."""

    username = None
    email = models.EmailField(unique=True)
    avatar_color = models.CharField(max_length=7, default="#1976D2")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    job_title = models.CharField(max_length=120, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def initials(self):
        first = (self.first_name or "")[:1]
        last = (self.last_name or "")[:1]
        return (first + last).upper() or self.email[:2].upper()
