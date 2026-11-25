from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import allocate_project


class UnifiedAdminConsoleTests(TestCase):
    def setUp(self):
        self.password = "SafePassword!327"
        self.admin = User.objects.create_user(
            username="admin_one",
            email="admin1@example.com",
            password=self.password,
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
            first_name="Alice",
            last_name="Reyes",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password=self.password,
            first_name="Bob",
            last_name="Cruz",
        )
        self.alice_project = NetworkProject.objects.create(
            owner=self.alice,
            name="Alice Campus LAN",
            base_network="10.10.0.0",
            prefix_length=24,
        )
        SubnetRequirement.objects.create(project=self.alice_project, name="Lab A", required_hosts=50)
        allocate_project(self.alice_project)

        self.bob_project = NetworkProject.objects.create(
            owner=self.bob,
            name="Bob Branch WAN",
            base_network="192.168.50.0",
            prefix_length=24,
        )

    def test_regular_user_cannot_access_admin_console_endpoints(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("dashboard:admin_user_create")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("dashboard:admin_user_detail", args=[self.bob.username])).status_code, 403
        )
        self.assertEqual(
            self.client.post(reverse("dashboard:admin_user_toggle_active", args=[self.bob.username])).status_code, 403
        )
        self.assertEqual(
            self.client.post(reverse("dashboard:admin_user_change_role", args=[self.bob.username])).status_code, 403
        )

    def test_admin_dashboard_lists_and_filters_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:admin"), {"q": "alice", "role": User.Role.USER})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([u.username for u in response.context["users"]], ["alice"])
        self.assertContains(response, "@alice")

    def test_user_to_projects_to_project_details_hierarchy(self):
        self.client.force_login(self.admin)
        user_resp = self.client.get(reverse("dashboard:admin_user_detail", args=[self.alice.username]))
        self.assertEqual(user_resp.status_code, 200)
        self.assertContains(user_resp, "Alice Campus LAN")
        self.assertNotContains(user_resp, "Bob Branch WAN")

        project_resp = self.client.get(
            reverse("dashboard:admin_user_project_detail", args=[self.alice.username, self.alice_project.slug])
        )
        self.assertEqual(project_resp.status_code, 200)
        self.assertContains(project_resp, "Admin Console")
        self.assertContains(project_resp, "@alice")
        self.assertContains(project_resp, "Read-only oversight")

        # Mismatched owner + project slug returns 404
        mismatch_resp = self.client.get(
            reverse("dashboard:admin_user_project_detail", args=[self.bob.username, self.alice_project.slug])
        )
        self.assertEqual(mismatch_resp.status_code, 404)

    def test_admin_projects_page_is_personal_to_admin(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("network_projects:list"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Alice Campus LAN")
        self.assertNotContains(resp, "Bob Branch WAN")

    def test_admin_can_toggle_active_and_change_role_for_other_users(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:admin_user_toggle_active", args=[self.alice.username]))
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_active)

        self.client.post(reverse("dashboard:admin_user_change_role", args=[self.bob.username]))
        self.bob.refresh_from_db()
        self.assertEqual(self.bob.role, User.Role.ADMIN)
        self.assertTrue(self.bob.is_staff)

    def test_admin_cannot_deactivate_or_demote_self(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:admin_user_toggle_active", args=[self.admin.username]))
        self.client.post(reverse("dashboard:admin_user_change_role", args=[self.admin.username]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_admin_can_create_new_account(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("dashboard:admin_user_create"),
            {
                "username": "charlie",
                "email": "charlie@example.com",
                "first_name": "Charlie",
                "last_name": "Santos",
                "contact_number": "09171234567",
                "role_record": User.Role.USER,
                "password1": "StrongPass!327",
                "password2": "StrongPass!327",
            },
        )
        created = User.objects.get(username="charlie")
        self.assertRedirects(resp, reverse("dashboard:admin_user_detail", args=[created.username]))
        self.assertEqual(created.role, User.Role.USER)
        self.assertFalse(created.is_staff)
