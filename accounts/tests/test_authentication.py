from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = "StrongLabPassword!327"
        self.user = User.objects.create_user(username="student", email="student@example.com", password=self.password)

    def test_valid_login_creates_session_and_routes_user(self):
        response = self.client.post(reverse("accounts:login"), {"username": "student", "password": self.password})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_invalid_login_shows_feedback(self):
        response = self.client.post(reverse("accounts:login"), {"username": "student", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check your username and password")

    def test_logout_requires_post_and_invalidates_session(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_external_next_url_is_not_followed(self):
        response = self.client.post(
            f'{reverse("accounts:login")}?next=https://malicious.example/steal',
            {"username": "student", "password": self.password, "next": "https://malicious.example/steal"},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))


class DashboardAuthorizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", email="student@example.com", password="SafePassword!327")
        self.admin = User.objects.create_user(
            username="administrator", email="admin@example.com", password="SafePassword!327", role=User.Role.ADMIN
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("accounts:user_dashboard"))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("accounts:user_dashboard")}')

    def test_regular_user_cannot_access_admin_dashboard(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:admin_dashboard")).status_code, 403)

    def test_admin_cannot_access_regular_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:user_dashboard")).status_code, 403)

    def test_dashboard_router_sends_each_role_to_its_dashboard(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("accounts:dashboard")), reverse("accounts:user_dashboard"))
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse("accounts:dashboard")), reverse("accounts:admin_dashboard"))
