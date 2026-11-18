from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from accounts.profile_photos import _auth_headers, delete_profile_photo, upload_profile_photo


class ProfilePhotoStorageTests(SimpleTestCase):
    def test_current_secret_key_uses_apikey_header_only(self):
        self.assertEqual(_auth_headers("sb_secret_example"), {"apikey": "sb_secret_example"})

    def test_legacy_service_role_key_keeps_bearer_header(self):
        self.assertEqual(
            _auth_headers("legacy-jwt"),
            {"apikey": "legacy-jwt", "Authorization": "Bearer legacy-jwt"},
        )

    def test_local_storage_uploads_and_deletes_photo(self):
        with TemporaryDirectory() as media_root, override_settings(
            PROFILE_PHOTO_STORAGE="local", MEDIA_ROOT=media_root
        ):
            photo = SimpleUploadedFile("profile.webp", b"local-photo", content_type="image/webp")
            photo.image_format = "WEBP"

            object_path = upload_profile_photo(42, photo)

            self.assertTrue(object_path.startswith("profile-photos/users/42/"))
            self.assertTrue(Path(media_root, object_path).exists())
            delete_profile_photo(object_path)
            self.assertFalse(Path(media_root, object_path).exists())
