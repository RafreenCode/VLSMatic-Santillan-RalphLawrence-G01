from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class UnifiedAdminRoutingTests(TestCase):
    def setUp(self):
        self.password = "SafeAdminPassword!327"
        self.admin_user = User.objects.create_superuser(
            username="siteadmin",
            email="siteadmin@example.com",
            password=self.password,
            role=User.Role.ADMIN,
        )
        self.regular_user = User.objects.create_user(
            username="regularuser",
            email="regular@example.com",
            password=self.password,
        )

    def test_admin_url_redirects_to_unified_admin_dashboard(self):
        response = self.client.get("/admin/", follow=True)
        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reverse("dashboard:admin")}',
        )

    def test_admin_login_url_redirects_to_unified_admin_dashboard(self):
        response = self.client.get("/admin/login/", follow=True)
        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reverse("dashboard:admin")}',
        )

    def test_authenticated_admin_visiting_admin_url_lands_on_unified_console(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/", follow=True)
        self.assertRedirects(response, reverse("dashboard:admin"))
        self.assertContains(response, "Unified Administration Console")
        self.assertContains(response, "User directory")

    def test_regular_user_visiting_admin_url_receives_403(self):
        self.client.force_login(self.regular_user)
        response = self.client.get("/admin/", follow=True)
        self.assertEqual(response.status_code, 403)
