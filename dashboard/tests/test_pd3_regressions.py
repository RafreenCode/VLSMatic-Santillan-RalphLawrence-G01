from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from accounts.models import GroupMembership, User, WorkspaceGroup
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import allocate_project


def _make_png_upload(name="avatar.png"):
    buf = BytesIO()
    Image.new("RGB", (64, 64), color=(0, 120, 140)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class PD3RegressionCoverageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "SafePassword!327"
        cls.admin = User.objects.create_user(
            username="pd3_admin",
            email="pd3admin@example.com",
            password=cls.password,
            role=User.Role.ADMIN,
            is_staff=True,
        )
        cls.alice = User.objects.create_user(
            username="pd3_alice",
            email="pd3alice@example.com",
            password=cls.password,
        )
        cls.bob = User.objects.create_user(
            username="pd3_bob",
            email="pd3bob@example.com",
            password=cls.password,
        )
        cls.project = NetworkProject.objects.create(
            owner=cls.alice,
            name="PD3 Core Network",
            base_network="10.30.0.0",
            prefix_length=24,
        )
        cls.requirement = SubnetRequirement.objects.create(
            project=cls.project,
            name="Core Lab",
            required_hosts=50,
        )
        allocate_project(cls.project)
        cls.group = WorkspaceGroup.objects.create(
            name="PD3 Cohort G1",
            created_by=cls.admin,
        )
        GroupMembership.objects.create(group=cls.group, user=cls.alice)

    def test_all_state_changing_endpoints_reject_get_requests(self):
        self.client.force_login(self.alice)
        user_post_urls = [
            reverse("network_projects:update", args=[self.project.slug]),
            reverse("network_projects:delete", args=[self.project.slug]),
            reverse("network_projects:calculate", args=[self.project.slug]),
            reverse("network_projects:requirement_create", args=[self.project.slug]),
            reverse("network_projects:requirement_update", args=[self.project.slug, self.requirement.pk]),
            reverse("network_projects:requirement_delete", args=[self.project.slug, self.requirement.pk]),
            reverse("dashboard:user_join_group"),
            reverse("dashboard:user_leave_group", args=[self.group.slug]),
        ]
        for url in user_post_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)

        self.client.force_login(self.admin)
        admin_post_urls = [
            reverse("dashboard:admin_group_delete", args=[self.group.slug]),
            reverse("dashboard:admin_group_regenerate_code", args=[self.group.slug]),
            reverse("dashboard:admin_group_toggle_joinable", args=[self.group.slug]),
            reverse("dashboard:admin_group_add_member", args=[self.group.slug]),
            reverse("dashboard:admin_group_remove_member", args=[self.group.slug, self.alice.username]),
            reverse("dashboard:admin_user_toggle_active", args=[self.alice.username]),
            reverse("dashboard:admin_user_change_role", args=[self.alice.username]),
        ]
        for url in admin_post_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)

    def test_last_active_admin_cannot_be_demoted_or_deactivated_via_form_or_actions(self):
        self.client.force_login(self.admin)

        form_resp = self.client.post(
            reverse("dashboard:admin_user_detail", args=[self.admin.username]),
            {
                "first_name": "Admin",
                "last_name": "User",
                "email": self.admin.email,
                "contact_number": "",
                "role_record": User.Role.USER,
            },
        )
        self.assertEqual(form_resp.status_code, 200)
        self.assertContains(form_resp, "cannot remove administrator access")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)
        self.assertTrue(self.admin.is_active)

    def test_group_deletion_preserves_member_accounts_and_projects(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("dashboard:admin_group_delete", args=[self.group.slug]))
        self.assertRedirects(resp, reverse("dashboard:admin_group_list"))
        self.assertFalse(WorkspaceGroup.objects.filter(pk=self.group.pk).exists())
        self.assertFalse(GroupMembership.objects.filter(group_id=self.group.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.alice.pk).exists())
        self.assertTrue(NetworkProject.objects.filter(pk=self.project.pk).exists())

    def test_regenerated_join_code_immediately_invalidates_previous_code(self):
        old_code = self.group.join_code
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:admin_group_regenerate_code", args=[self.group.slug]))
        self.group.refresh_from_db()
        self.assertNotEqual(self.group.join_code, old_code)

        self.client.force_login(self.bob)
        self.client.post(reverse("dashboard:user_join_group"), {"join_code": old_code})
        self.assertFalse(GroupMembership.objects.filter(group=self.group, user=self.bob).exists())

        self.client.post(reverse("dashboard:user_join_group"), {"join_code": self.group.join_code})
        self.assertTrue(GroupMembership.objects.filter(group=self.group, user=self.bob).exists())

    def test_profile_duplicate_email_conflict_cleans_up_uploaded_photo_and_preserves_role(self):
        self.client.force_login(self.alice)
        unique_error = IntegrityError("duplicate key")
        unique_error.__cause__ = type("FakePgError", (Exception,), {"sqlstate": "23505"})()

        with (
            patch("accounts.views.upload_profile_photo", return_value="profiles/temp-upload.webp"),
            patch("accounts.views.delete_profile_photo") as mock_delete,
            patch("accounts.models.User.save", side_effect=unique_error),
        ):
            resp = self.client.post(
                reverse("accounts:profile"),
                {
                    "first_name": "Alice",
                    "last_name": "Updated",
                    "email": "fresh-email@example.com",
                    "contact_number": "",
                    "profile_photo": _make_png_upload(),
                },
            )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "An account with this email address already exists.")
        mock_delete.assert_called_once_with("profiles/temp-upload.webp")
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "pd3alice@example.com")
        self.assertEqual(self.alice.role, User.Role.USER)

    def test_profile_unrelated_integrity_error_is_reraised(self):
        self.client.force_login(self.alice)
        with patch("accounts.models.User.save", side_effect=IntegrityError("unexpected db failure")):
            with self.assertRaises(IntegrityError):
                self.client.post(
                    reverse("accounts:profile"),
                    {
                        "first_name": "Alice",
                        "last_name": "Reyes",
                        "email": self.alice.email,
                        "contact_number": "",
                    },
                )
