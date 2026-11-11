from django.test import TestCase
from django.urls import reverse

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
