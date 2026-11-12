import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


class ProfilePhotoStorageError(Exception):
    """Raised when a profile photo cannot be persisted in Supabase Storage."""


IMAGE_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def _storage_config() -> tuple[str, str, str]:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ProfilePhotoStorageError("Profile photo storage is not configured yet.")
    return (
        settings.SUPABASE_URL.rstrip("/"),
        settings.SUPABASE_SERVICE_ROLE_KEY,
        settings.SUPABASE_PROFILE_BUCKET,
    )


def upload_profile_photo(user_id: int, photo: UploadedFile) -> str:
    base_url, service_key, bucket = _storage_config()
    extension = IMAGE_EXTENSIONS[photo.image_format]
    object_path = f"users/{user_id}/{uuid4().hex}.{extension}"
    endpoint = (
        f"{base_url}/storage/v1/object/{quote(bucket, safe='')}/"
        f"{quote(object_path, safe='/')}"
    )
    request = Request(
        endpoint,
        data=photo.read(),
        method="POST",
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": photo.content_type or "application/octet-stream",
            "x-upsert": "false",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            if response.status not in {200, 201}:
                raise ProfilePhotoStorageError("The photo could not be saved. Try again.")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ProfilePhotoStorageError("The photo could not be saved. Try again.") from exc
    finally:
        photo.seek(0)
    return object_path


def delete_profile_photo(object_path: str) -> None:
    if not object_path:
        return
    base_url, service_key, bucket = _storage_config()
    endpoint = f"{base_url}/storage/v1/object/{quote(bucket, safe='')}"
    request = Request(
        endpoint,
        data=json.dumps({"prefixes": [object_path]}).encode("utf-8"),
        method="DELETE",
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=20):
            return
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ProfilePhotoStorageError("The previous photo could not be removed.") from exc
