import secrets
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.storage import default_storage
from django.db import models
from django.db.models.functions import Lower
from django.utils.text import slugify


JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SLUG_TOKEN_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def generate_public_slug(name: str, fallback: str = "item") -> str:
    base = slugify(name or "")[:96].strip("-") or fallback
    token = "".join(secrets.choice(SLUG_TOKEN_ALPHABET) for _ in range(6))
    return f"{base}-{token}"


def normalize_join_code(raw_code: str) -> str:
    cleaned = "".join(ch for ch in (raw_code or "").upper().strip() if ch.isalnum())
    if len(cleaned) == 8:
        return f"{cleaned[:4]}-{cleaned[4:]}"
    return cleaned


def generate_join_code() -> str:
    chars = "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(8))
    return f"{chars[:4]}-{chars[4:]}"


class Role(models.Model):
    USER = "user"
    ADMIN = "admin"

    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__in=("user", "admin")),
                name="role_code_user_or_admin",
            )
        ]

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


class WorkspaceGroup(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, unique=True, db_index=True, editable=False)
    description = models.TextField(blank=True, max_length=500)
    join_code = models.CharField(max_length=16, unique=True, db_index=True, default=generate_join_code)
    is_joinable = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_workspace_groups",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="GroupMembership",
        through_fields=("group", "user"),
        related_name="workspace_groups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(Lower("name"), name="unique_workspace_group_name_ci"),
        ]

    def __str__(self):
        return f"{self.name} ({self.join_code})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug(self.name)
        if not self.join_code:
            self.join_code = self.generate_unique_join_code()
        else:
            self.join_code = normalize_join_code(self.join_code)
        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_slug(cls, name: str) -> str:
        for _ in range(25):
            candidate = generate_public_slug(name, fallback="group")
            if not cls.objects.filter(slug=candidate).exists():
                return candidate
        raise RuntimeError("Could not generate a unique group slug.")

    @classmethod
    def generate_unique_join_code(cls) -> str:
        for _ in range(25):
            candidate = generate_join_code()
            if not cls.objects.filter(join_code=candidate).exists():
                return candidate
        raise RuntimeError("Could not generate a unique group join code.")

    def regenerate_join_code(self) -> str:
        self.join_code = self.generate_unique_join_code()
        self.save(update_fields=["join_code", "updated_at"])
        return self.join_code


class GroupMembership(models.Model):
    group = models.ForeignKey(
        WorkspaceGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="added_group_memberships",
    )

    class Meta:
        ordering = ("-joined_at",)
        constraints = [
            models.UniqueConstraint(fields=("group", "user"), name="unique_user_per_workspace_group"),
        ]
        indexes = [
            models.Index(fields=("group", "joined_at"), name="membership_group_joined_idx"),
            models.Index(fields=("user", "joined_at"), name="membership_user_joined_idx"),
        ]

    def __str__(self):
        return f"{self.user} in {self.group.name}"
