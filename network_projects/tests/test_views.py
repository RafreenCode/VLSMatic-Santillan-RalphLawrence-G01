from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement


class ProjectViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("student", "student@example.com", "SafePassword!327")
        self.other = User.objects.create_user("other", "other@example.com", "SafePassword!327")
        self.admin = User.objects.create_user("administrator", "admin@example.com", "SafePassword!327", role=User.Role.ADMIN)
        self.project = NetworkProject.objects.create(owner=self.user, name="My plan", base_network="192.168.1.0", prefix_length=24)
        self.other_project = NetworkProject.objects.create(owner=self.other, name="Private plan", base_network="10.0.0.0", prefix_length=16)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("network_projects:list"))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("network_projects:list")}')

    def test_list_contains_only_current_users_projects(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("network_projects:list"))
        self.assertContains(response, "My plan")
        self.assertNotContains(response, "Private plan")

    def test_user_can_create_project(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("network_projects:create"), {"name": "Branch office", "description": "", "base_network": "172.16.0.0", "prefix_length": 20})
        project = NetworkProject.objects.get(name="Branch office")
        self.assertEqual(project.owner, self.user)
        self.assertRedirects(response, reverse("network_projects:detail", args=[project.pk]))

    def test_user_cannot_view_or_modify_another_users_project(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("network_projects:detail", args=[self.other_project.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("network_projects:update", args=[self.other_project.pk]), {"name": "Stolen", "base_network": "10.0.0.0", "prefix_length": 16}).status_code, 404)
        self.assertEqual(self.client.post(reverse("network_projects:delete", args=[self.other_project.pk])).status_code, 404)

    def test_user_can_add_update_and_delete_requirement(self):
        self.client.force_login(self.user)
        create_response = self.client.post(reverse("network_projects:requirement_create", args=[self.project.pk]), {"name": "Lab A", "required_hosts": 30})
        requirement = SubnetRequirement.objects.get(project=self.project)
        self.assertRedirects(create_response, reverse("network_projects:detail", args=[self.project.pk]))
        self.client.post(reverse("network_projects:requirement_update", args=[requirement.pk]), {"name": "Lab B", "required_hosts": 40})
        requirement.refresh_from_db()
        self.assertEqual(requirement.name, "Lab B")
        self.client.post(reverse("network_projects:requirement_delete", args=[requirement.pk]))
        self.assertFalse(SubnetRequirement.objects.filter(pk=requirement.pk).exists())

    def test_admin_has_read_only_project_visibility(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("network_projects:list")), "My plan")
        self.assertEqual(self.client.get(reverse("network_projects:detail", args=[self.project.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("network_projects:update", args=[self.project.pk])).status_code, 403)

    def test_calculate_requires_post_and_persists_result(self):
        requirement = SubnetRequirement.objects.create(project=self.project, name="Lab", required_hosts=50)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("network_projects:calculate", args=[self.project.pk])).status_code, 405)
        response = self.client.post(reverse("network_projects:calculate", args=[self.project.pk]))
        requirement.refresh_from_db()
        self.assertRedirects(response, reverse("network_projects:detail", args=[self.project.pk]))
        self.assertEqual(requirement.network_address, "192.168.1.0")
        self.assertEqual(requirement.prefix_length, 26)

    def test_user_cannot_calculate_another_users_project(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("network_projects:calculate", args=[self.other_project.pk]))
        self.assertEqual(response.status_code, 404)

