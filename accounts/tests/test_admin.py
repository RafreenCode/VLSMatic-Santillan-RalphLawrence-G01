from django.contrib import admin
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.admin import VLSMaticUserAdmin
from accounts.models import User


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class AdminInterfaceTests(TestCase):
    def setUp(self):
        self.password = "SafeAdminPassword!327"
        self.superuser = User.objects.create_superuser(
            username="siteadmin",
            email="siteadmin@example.com",
            password=self.password,
            role=User.Role.ADMIN,
        )

    def test_admin_login_uses_vlsmatic_branding_and_guidance(self):
        response = self.client.get(reverse("admin:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/login.html")
        self.assertContains(response, "VLSMatic")
        self.assertContains(response, "Sign in to administration")
        self.assertContains(response, "css/admin.css")

    def test_admin_index_requires_staff_authentication(self):
        response = self.client.get(reverse("admin:index"))

        self.assertRedirects(response, f'{reverse("admin:login")}?next={reverse("admin:index")}')

    def test_admin_index_uses_custom_workspace_after_login(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/index.html")
        self.assertContains(response, "Administration workspace")
        self.assertContains(response, "View site")

    def test_user_admin_has_operational_search_and_filters(self):
        user_admin = admin.site._registry[User]

        self.assertIsInstance(user_admin, VLSMaticUserAdmin)
        self.assertIn("email", user_admin.search_fields)
        self.assertIn("role", user_admin.list_filter)
        self.assertIn("date_joined", user_admin.readonly_fields)
