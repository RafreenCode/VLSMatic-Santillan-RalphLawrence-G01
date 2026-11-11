from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "Regular User"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    contact_number = models.CharField(max_length=30, blank=True)

    @property
    def is_vlsmatic_admin(self) -> bool:
        return self.role == self.Role.ADMIN
