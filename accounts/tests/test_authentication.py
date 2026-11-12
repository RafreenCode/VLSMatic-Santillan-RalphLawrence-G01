from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = "StrongLabPassword!327"
        self.user = User.objects.create_user(username="student", email="student@example.com", password=self.password)

    def test_home_routes_anonymous_visitors_to_login(self):
        response = self.client.get(reverse("accounts:home"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_home_routes_authenticated_users_to_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:home"))
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_valid_login_creates_session_and_routes_user(self):
        response = self.client.post(reverse("accounts:login"), {"username": "student", "password": self.password})
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)
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
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)
