from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class DashboardAuthorizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", email="student@example.com", password="SafePassword!327")
        self.admin = User.objects.create_user(
            username="administrator", email="admin@example.com", password="SafePassword!327", role=User.Role.ADMIN
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("dashboard:user"))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("dashboard:user")}')

    def test_regular_user_cannot_access_admin_dashboard(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dashboard:admin")).status_code, 403)

    def test_admin_cannot_access_regular_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("dashboard:user")).status_code, 403)

    def test_dashboard_router_sends_each_role_to_its_dashboard(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("dashboard:home")), reverse("dashboard:user"))
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse("dashboard:home")), reverse("dashboard:admin"))
