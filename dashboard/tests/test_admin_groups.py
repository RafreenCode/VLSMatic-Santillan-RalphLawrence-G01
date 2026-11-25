from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import GroupMembership, User, WorkspaceGroup, normalize_join_code
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import allocate_project


class AdminGroupsAndJoinCodeTests(TestCase):
    def setUp(self):
        self.password = "SafePassword!327"
        self.admin = User.objects.create_user(
            username="admin_coord",
            email="coord@example.com",
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
            name="Alice Lab Network",
            base_network="10.20.0.0",
            prefix_length=24,
        )
        SubnetRequirement.objects.create(project=self.alice_project, name="Lab 1", required_hosts=30)
        allocate_project(self.alice_project)

        self.bob_project = NetworkProject.objects.create(
            owner=self.bob,
            name="Bob Standalone Network",
            base_network="172.16.0.0",
            prefix_length=24,
        )

    def test_join_code_normalization_and_uniqueness_constraints(self):
        self.assertEqual(normalize_join_code(" abcd1234 "), "ABCD-1234")
        self.assertEqual(normalize_join_code("ab-cd-12-34"), "ABCD-1234")

        group = WorkspaceGroup.objects.create(name="CSIT327 G01", created_by=self.admin)
        self.assertEqual(len(group.join_code), 9)
        self.assertEqual(group.join_code[4], "-")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkspaceGroup.objects.create(name="csit327 g01", created_by=self.admin)

        GroupMembership.objects.create(group=group, user=self.alice)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GroupMembership.objects.create(group=group, user=self.alice)

    def test_admin_can_create_edit_regenerate_pause_and_delete_group(self):
        self.client.force_login(self.admin)

        create_resp = self.client.post(
            reverse("dashboard:admin_group_create"),
            {"name": "Networking Lab A", "description": "Tuesday cohort", "is_joinable": True},
        )
        group = WorkspaceGroup.objects.get(name="Networking Lab A")
        self.assertRedirects(create_resp, reverse("dashboard:admin_group_detail", args=[group.pk]))
        old_code = group.join_code

        self.client.post(reverse("dashboard:admin_group_regenerate_code", args=[group.pk]))
        group.refresh_from_db()
        self.assertNotEqual(group.join_code, old_code)

        self.client.post(reverse("dashboard:admin_group_toggle_joinable", args=[group.pk]))
        group.refresh_from_db()
        self.assertFalse(group.is_joinable)

        self.client.post(
            reverse("dashboard:admin_group_update", args=[group.pk]),
            {"name": "Networking Lab A Updated", "description": "Updated", "is_joinable": True},
        )
        group.refresh_from_db()
        self.assertEqual(group.name, "Networking Lab A Updated")
        self.assertTrue(group.is_joinable)

        del_resp = self.client.post(reverse("dashboard:admin_group_delete", args=[group.pk]))
        self.assertRedirects(del_resp, reverse("dashboard:admin_group_list"))
        self.assertFalse(WorkspaceGroup.objects.filter(pk=group.pk).exists())

    def test_regular_user_can_join_by_code_and_leave_group(self):
        group = WorkspaceGroup.objects.create(name="CSIT327 Section G01", created_by=self.admin)
        raw_lowercase = group.join_code.replace("-", "").lower()

        self.client.force_login(self.alice)
        # Valid lowercase/unhyphenated code works
        resp = self.client.post(reverse("dashboard:user_join_group"), {"join_code": raw_lowercase}, follow=True)
        self.assertRedirects(resp, reverse("dashboard:user"))
        self.assertTrue(GroupMembership.objects.filter(group=group, user=self.alice).exists())
        self.assertContains(resp, "CSIT327 Section G01")

        # Leaving removes membership cleanly
        leave_resp = self.client.post(reverse("dashboard:user_leave_group", args=[group.pk]), follow=True)
        self.assertRedirects(leave_resp, reverse("dashboard:user"))
        self.assertFalse(GroupMembership.objects.filter(group=group, user=self.alice).exists())

    def test_closed_group_or_invalid_code_is_rejected(self):
        closed_group = WorkspaceGroup.objects.create(
            name="Closed Cohort", is_joinable=False, created_by=self.admin
        )
        self.client.force_login(self.alice)

        self.client.post(reverse("dashboard:user_join_group"), {"join_code": closed_group.join_code})
        self.assertFalse(GroupMembership.objects.filter(group=closed_group, user=self.alice).exists())

        self.client.post(reverse("dashboard:user_join_group"), {"join_code": "ZZZZ-9999"})
        self.assertEqual(GroupMembership.objects.filter(user=self.alice).count(), 0)

    def test_role_isolation_on_group_endpoints(self):
        group = WorkspaceGroup.objects.create(name="Isolated Group", created_by=self.admin)

        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("dashboard:admin_group_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:admin_group_detail", args=[group.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("dashboard:admin_group_delete", args=[group.pk])).status_code, 403)

        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(reverse("dashboard:user_join_group"), {"join_code": group.join_code}).status_code, 403
        )

    def test_group_to_users_to_projects_to_project_details_flow(self):
        group = WorkspaceGroup.objects.create(name="CSIT327 Lab B", created_by=self.admin)
        self.client.force_login(self.admin)

        # Admin enrolls Alice manually
        self.client.post(reverse("dashboard:admin_group_add_member", args=[group.pk]), {"user": self.alice.pk})
        self.assertTrue(GroupMembership.objects.filter(group=group, user=self.alice, added_by=self.admin).exists())

        # Group detail shows Alice & Alice's project, NOT Bob or Bob's project
        group_resp = self.client.get(reverse("dashboard:admin_group_detail", args=[group.pk]))
        self.assertEqual(group_resp.status_code, 200)
        self.assertContains(group_resp, "@alice")
        self.assertContains(group_resp, "Alice Lab Network")
        self.assertNotContains(group_resp, "Bob Standalone Network")

        # User detail with ?group= renders Group breadcrumb
        user_resp = self.client.get(reverse("dashboard:admin_user_detail", args=[self.alice.pk]), {"group": group.pk})
        self.assertEqual(user_resp.status_code, 200)
        self.assertContains(user_resp, "CSIT327 Lab B")
        self.assertContains(user_resp, "Alice Lab Network")

        # Project detail with ?group= renders full Group -> User -> Project breadcrumb
        proj_resp = self.client.get(
            reverse("network_projects:detail", args=[self.alice_project.pk]), {"group": group.pk}
        )
        self.assertEqual(proj_resp.status_code, 200)
        self.assertContains(proj_resp, "CSIT327 Lab B")
        self.assertContains(proj_resp, "@alice")
        self.assertContains(proj_resp, "Read-only oversight")

        # Admin Users tab filters by group
        users_resp = self.client.get(reverse("dashboard:admin_user_list"), {"group": group.pk})
        self.assertEqual(users_resp.status_code, 200)
        self.assertEqual([u.username for u in users_resp.context["users"]], ["alice"])
        self.assertNotContains(users_resp, "Review all projects")

        # Remove member from group
        self.client.post(reverse("dashboard:admin_group_remove_member", args=[group.pk, self.alice.pk]))
        self.assertFalse(GroupMembership.objects.filter(group=group, user=self.alice).exists())
