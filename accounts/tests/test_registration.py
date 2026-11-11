from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class RegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:register")
        self.valid_data = {
            "username": "networkstudent",
            "email": "student@example.com",
            "first_name": "Net",
            "last_name": "Student",
            "password1": "StrongLabPassword!327",
            "password2": "StrongLabPassword!327",
        }

    def test_user_can_register_as_regular_user(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(username="networkstudent")
        self.assertEqual(user.role, User.Role.USER)
        self.assertTrue(user.check_password(self.valid_data["password1"]))
        self.assertNotEqual(user.password, self.valid_data["password1"])

    def test_required_fields_are_validated(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "username", "This field is required.")
        self.assertFormError(response.context["form"], "email", "This field is required.")
        self.assertFormError(response.context["form"], "password1", "This field is required.")

    def test_invalid_email_is_rejected(self):
        data = {**self.valid_data, "email": "not-an-email"}
        response = self.client.post(self.url, data)
        self.assertFormError(response.context["form"], "email", "Enter a valid email address.")

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username="networkstudent", email="first@example.com", password="SafePassword!327")
        data = {**self.valid_data, "email": "different@example.com"}
        response = self.client.post(self.url, data)
        self.assertFormError(response.context["form"], "username", "A user with that username already exists.")

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(username="existing", email="student@example.com", password="SafePassword!327")
        data = {**self.valid_data, "username": "different", "email": "STUDENT@example.com"}
        response = self.client.post(self.url, data)
        self.assertFormError(response.context["form"], "email", "An account with this email address already exists.")

    def test_mismatched_passwords_are_rejected(self):
        data = {**self.valid_data, "password2": "DifferentPassword!327"}
        response = self.client.post(self.url, data)
        self.assertFormError(response.context["form"], "password2", "The two password fields didn’t match.")

    def test_public_form_cannot_assign_admin_role(self):
        data = {**self.valid_data, "role": User.Role.ADMIN, "is_superuser": True}
        self.client.post(self.url, data)
        user = User.objects.get(username="networkstudent")
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
