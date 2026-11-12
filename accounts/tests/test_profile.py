from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from accounts.forms import ProfileForm
from accounts.models import User


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="SafePassword!327",
            first_name="Net",
            last_name="Student",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="SafePassword!327",
        )
        self.url = reverse("accounts:profile")

    @staticmethod
    def profile_photo(name="profile.png"):
        content = BytesIO()
        Image.new("RGB", (32, 32), "#d7a33d").save(content, format="PNG")
        return SimpleUploadedFile(name, content.getvalue(), content_type="image/png")

    def test_profile_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={self.url}')

    def test_user_can_update_own_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            {"first_name": "Network", "last_name": "Learner", "email": "updated@example.com", "contact_number": "+63 917 555 0101"},
        )
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Network")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.contact_number, "+63 917 555 0101")

    def test_duplicate_email_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            {"first_name": "Net", "last_name": "Student", "email": "OTHER@example.com", "contact_number": ""},
        )
        self.assertFormError(response.context["form"], "email", "An account with this email address already exists.")

    @patch("accounts.views.upload_profile_photo", return_value="users/1/photo.png")
    def test_user_can_upload_own_profile_photo(self, upload_photo):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            {
                "first_name": "Net",
                "last_name": "Student",
                "email": "student@example.com",
                "contact_number": "",
                "profile_photo": self.profile_photo(),
            },
        )
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_photo_path, "users/1/photo.png")
        self.assertEqual(upload_photo.call_args.args[0], self.user.pk)

    @patch("accounts.views.delete_profile_photo")
    def test_user_can_remove_own_profile_photo(self, delete_photo):
        self.user.profile_photo_path = "users/1/old.png"
        self.user.save(update_fields=["profile_photo_path"])
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            {
                "first_name": "Net",
                "last_name": "Student",
                "email": "student@example.com",
                "contact_number": "",
                "remove_profile_photo": "on",
            },
        )
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_photo_path, "")
        delete_photo.assert_called_once_with("users/1/old.png")

    def test_non_image_profile_photo_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            {
                "first_name": "Net",
                "last_name": "Student",
                "email": "student@example.com",
                "contact_number": "",
                "profile_photo": SimpleUploadedFile("not-an-image.png", b"not an image", content_type="image/png"),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "profile_photo", "Upload a valid image. The file you uploaded was either not an image or a corrupted image.")

    def test_profile_route_exposes_no_user_identifier(self):
        self.assertNotIn("<", self.url)
        self.assertNotIn(str(self.other_user.pk), self.url)

    def test_profile_form_cannot_change_privileges_or_identity(self):
        form = ProfileForm(
            data={
                "first_name": "Net",
                "last_name": "Student",
                "email": "student@example.com",
                "contact_number": "",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "username": "hijacked",
                "profile_photo_path": "users/other/hijacked.png",
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid())
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.USER)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.username, "student")
        self.assertEqual(self.user.profile_photo_path, "")
