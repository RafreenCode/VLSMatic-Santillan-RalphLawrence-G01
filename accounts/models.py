from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from urllib.parse import quote


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "Regular User"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    contact_number = models.CharField(max_length=30, blank=True)
    profile_photo_path = models.CharField(max_length=500, blank=True)

    @property
    def is_vlsmatic_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def profile_photo_url(self) -> str:
        if not self.profile_photo_path or not settings.SUPABASE_URL:
            return ""
        bucket = quote(settings.SUPABASE_PROFILE_BUCKET, safe="")
        path = quote(self.profile_photo_path, safe="/")
        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{bucket}/{path}"
