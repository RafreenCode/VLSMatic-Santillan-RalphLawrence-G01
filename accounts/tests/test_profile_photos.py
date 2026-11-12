from django.test import SimpleTestCase

from accounts.profile_photos import _auth_headers


class ProfilePhotoStorageTests(SimpleTestCase):
    def test_current_secret_key_uses_apikey_header_only(self):
        self.assertEqual(_auth_headers("sb_secret_example"), {"apikey": "sb_secret_example"})

    def test_legacy_service_role_key_keeps_bearer_header(self):
        self.assertEqual(
            _auth_headers("legacy-jwt"),
            {"apikey": "legacy-jwt", "Authorization": "Bearer legacy-jwt"},
        )
