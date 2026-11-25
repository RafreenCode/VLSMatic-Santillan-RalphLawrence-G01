from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import allocate_project


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
        response = self.client.post(
            reverse("network_projects:create"),
            {"name": "Branch office", "description": "", "base_network": "172.16.0.0", "prefix_length": 20},
        )
        project = NetworkProject.objects.get(name="Branch office")
        self.assertEqual(project.owner, self.user)
        self.assertTrue(project.slug.startswith("branch-office-"))
        self.assertRedirects(response, reverse("network_projects:detail", args=[project.slug]))

    def test_integer_id_url_enumeration_returns_404(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/projects/100/").status_code, 404)
        self.assertEqual(self.client.get(f"/projects/{self.project.pk}/").status_code, 404)

    def test_user_cannot_view_or_modify_another_users_project(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("network_projects:detail", args=[self.other_project.slug])).status_code, 404)
        self.assertEqual(
            self.client.post(
                reverse("network_projects:update", args=[self.other_project.slug]),
                {"name": "Stolen", "base_network": "10.0.0.0", "prefix_length": 16},
            ).status_code,
            404,
        )
        self.assertEqual(self.client.post(reverse("network_projects:delete", args=[self.other_project.slug])).status_code, 404)

    def test_user_can_add_update_and_delete_requirement(self):
        self.client.force_login(self.user)
        create_response = self.client.post(
            reverse("network_projects:requirement_create", args=[self.project.slug]),
            {"name": "Lab A", "required_hosts": 30},
        )
        requirement = SubnetRequirement.objects.get(project=self.project)
        self.assertRedirects(create_response, reverse("network_projects:detail", args=[self.project.slug]))
        self.client.post(
            reverse("network_projects:requirement_update", args=[self.project.slug, requirement.pk]),
            {"name": "Lab B", "required_hosts": 40},
        )
        requirement.refresh_from_db()
        self.assertEqual(requirement.name, "Lab B")
        self.client.post(reverse("network_projects:requirement_delete", args=[self.project.slug, requirement.pk]))
        self.assertFalse(SubnetRequirement.objects.filter(pk=requirement.pk).exists())

    def test_admin_has_read_only_project_visibility(self):
        admin_project = NetworkProject.objects.create(
            owner=self.admin, name="Admin Personal Plan", base_network="10.99.0.0", prefix_length=24
        )
        self.client.force_login(self.admin)
        list_resp = self.client.get(reverse("network_projects:list"))
        self.assertContains(list_resp, "Admin Personal Plan")
        self.assertNotContains(list_resp, "My plan")
        self.assertEqual(self.client.get(reverse("network_projects:update", args=[admin_project.slug])).status_code, 302)
        detail_resp = self.client.get(reverse("network_projects:detail", args=[self.project.slug]), follow=True)
        self.assertRedirects(
            detail_resp,
            reverse("dashboard:admin_user_project_detail", args=[self.user.username, self.project.slug]),
        )
        self.assertEqual(self.client.get(reverse("network_projects:update", args=[self.project.slug])).status_code, 403)

    def test_calculate_requires_post_and_persists_result(self):
        requirement = SubnetRequirement.objects.create(project=self.project, name="Lab", required_hosts=50)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("network_projects:calculate", args=[self.project.slug])).status_code, 405)
        response = self.client.post(reverse("network_projects:calculate", args=[self.project.slug]))
        self.assertRedirects(response, reverse("network_projects:detail", args=[self.project.slug]))
        self.assertEqual(requirement.allocation.network_address, "192.168.1.0")
        self.assertEqual(requirement.allocation.prefix_length, 26)

    def test_user_cannot_calculate_another_users_project(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("network_projects:calculate", args=[self.other_project.slug]))
        self.assertEqual(response.status_code, 404)

    def test_project_filters_are_cumulative(self):
        NetworkProject.objects.create(owner=self.user, name="Branch plan", base_network="172.16.0.0", prefix_length=16)
        self.client.force_login(self.user)
        response = self.client.get(reverse("network_projects:list"), {"name": "branch", "network": "172.16.0.0"})
        self.assertContains(response, "Branch plan")
        self.assertNotContains(response, "My plan")

    def test_invalid_network_filter_shows_feedback(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("network_projects:list"), {"network": "invalid"})
        self.assertContains(response, "Enter a valid IPv4 address")

    def test_failed_automatic_recalculation_rolls_back_requirement_edit(self):
        SubnetRequirement.objects.create(project=self.project, name="First", required_hosts=100)
        second = SubnetRequirement.objects.create(project=self.project, name="Second", required_hosts=100)
        allocate_project(self.project)
        old_run = self.project.calculation_run.pk
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("network_projects:requirement_update", args=[self.project.slug, second.pk]),
            {"name": "Second", "required_hosts": 200},
            follow=True,
        )
        second.refresh_from_db()
        self.project.refresh_from_db()
        self.assertRedirects(response, reverse("network_projects:detail", args=[self.project.slug]))
        self.assertEqual(second.required_hosts, 100)
        self.assertEqual(self.project.calculation_run.pk, old_run)
        self.assertContains(response, "data-studio-warning-modal")
        self.assertContains(response, "exceed this network")

    def test_detail_exposes_only_persisted_allocation_geometry(self):
        requirement = SubnetRequirement.objects.create(project=self.project, name="Studio", required_hosts=30)
        allocate_project(self.project)
        self.client.force_login(self.user)
        response = self.client.get(reverse("network_projects:detail", args=[self.project.slug]))
        visualization = response.context["visualization_data"]
        self.assertEqual(len(visualization), 1)
        self.assertEqual(visualization[0]["id"], requirement.pk)
        self.assertEqual(visualization[0]["network"], "192.168.1.0")
        self.assertEqual(visualization[0]["prefix"], 27)
        self.assertEqual(visualization[0]["relative_offset"], 0.0)
        self.assertEqual(visualization[0]["relative_span"], 0.125)
        self.assertContains(response, "allocation-visualization-data")

    def test_navigation_marks_active_projects_section(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("network_projects:list"))
        self.assertContains(response, f'href="{reverse("network_projects:list")}" aria-current="page"')

    def test_detail_renders_server_side_proportional_segments(self):
        SubnetRequirement.objects.create(project=self.project, name="Studio", required_hosts=30)
        allocate_project(self.project)
        self.client.force_login(self.user)
        response = self.client.get(reverse("network_projects:detail", args=[self.project.slug]))
        self.assertContains(response, 'class="hero-seg hero-seg--0 is-selected"')
        self.assertContains(response, 'data-flex-grow="32"')
        self.assertContains(response, "Studio, 192.168.1.0/27, 32 addresses")

    def test_studio_quick_add_error_returns_in_page_warning_modal(self):
        SubnetRequirement.objects.create(project=self.project, name="Office 6", required_hosts=30)
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("network_projects:requirement_create", args=[self.project.slug]),
            {"name": "Office 6", "required_hosts": 30, "from_studio": "1"},
            follow=True,
        )
        self.assertRedirects(response, reverse("network_projects:detail", args=[self.project.slug]))
        self.assertContains(response, "data-studio-warning-modal")
        self.assertContains(response, "This project already has a subnet with that name.")

    def test_detail_renders_modern_controls_brand_lockup_and_copy_actions(self):
        SubnetRequirement.objects.create(project=self.project, name="Studio", required_hosts=30)
        allocate_project(self.project)
        self.client.force_login(self.user)
        response = self.client.get(reverse("network_projects:detail", args=[self.project.slug]))
        self.assertContains(response, 'src="/static/img/vlsmatic-logo.png"')
        self.assertNotContains(response, "vlsmatic-icon.png")
        self.assertNotContains(response, "vlsmatic-wordmark.png")
        self.assertContains(response, 'class="back-pill"')
        self.assertContains(response, 'class="button button--danger-ghost"')
        self.assertContains(response, 'data-copy-value="192.168.1.0/27"')
        self.assertContains(response, "data-map-tooltip")
