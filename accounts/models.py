from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from django.core.files.storage import default_storage
from urllib.parse import quote


class Role(models.Model):
    USER = "user"
    ADMIN = "admin"

    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "Regular User"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    role_record = models.ForeignKey(
        "accounts.Role",
        db_column="role_code",
        default=Role.USER,
        on_delete=models.PROTECT,
        related_name="users",
    )
    contact_number = models.CharField(max_length=30, blank=True)
    profile_photo_path = models.CharField(max_length=500, blank=True)

    @property
    def is_vlsmatic_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def role(self):
        return self.role_record_id

    @role.setter
    def role(self, value):
        self.role_record_id = getattr(value, "pk", value)

    @property
    def profile_photo_url(self) -> str:
        if not self.profile_photo_path:
            return ""
        if settings.PROFILE_PHOTO_STORAGE == "local":
            return default_storage.url(self.profile_photo_path)
        if not settings.SUPABASE_URL:
            return ""
        bucket = quote(settings.SUPABASE_PROFILE_BUCKET, safe="")
        path = quote(self.profile_photo_path, safe="/")
        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{bucket}/{path}"
