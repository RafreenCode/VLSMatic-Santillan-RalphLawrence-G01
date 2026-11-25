from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import allocate_project


class DashboardContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("planner", "planner@example.com", "SafePassword!327")
        self.other = User.objects.create_user("other-planner", "other@example.com", "SafePassword!327")

    def test_empty_dashboard_exposes_zero_metrics_and_empty_state(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:user"))
        self.assertEqual(response.context["project_count"], 0)
        self.assertEqual(response.context["subnet_count"], 0)
        self.assertEqual(response.context["allocated_address_count"], 0)
        self.assertContains(response, "Your first address space is waiting")

    def test_dashboard_metrics_are_real_and_owner_isolated(self):
        project = NetworkProject.objects.create(
            owner=self.user, name="Campus", base_network="10.0.0.0", prefix_length=24
        )
        SubnetRequirement.objects.create(project=project, name="Lab", required_hosts=50)
        allocate_project(project)
        NetworkProject.objects.create(
            owner=self.other, name="Private", base_network="172.16.0.0", prefix_length=24
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:user"))
        self.assertEqual(response.context["project_count"], 1)
        self.assertEqual(response.context["subnet_count"], 1)
        self.assertEqual(response.context["active_plan_count"], 1)
        self.assertEqual(response.context["allocated_address_count"], 64)
        self.assertEqual(response.context["resume_summary"]["allocated_addresses"], 64)
        self.assertEqual(response.context["resume_summary"]["remaining_addresses"], 192)
        self.assertEqual(response.context["resume_visualization"][0]["relative_span"], 0.25)
        self.assertContains(response, "Latest saved plan")
        self.assertContains(response, "Open plan")
        self.assertContains(response, "Campus")
        self.assertNotContains(response, "Private")
        plans_payload = response.context["dashboard_plans_data"]
        self.assertEqual(len(plans_payload), 1)
        self.assertEqual(plans_payload[0]["cidr"], "10.0.0.0/24")
        self.assertEqual(plans_payload[0]["allocations"][0]["network"], "10.0.0.0")
        self.assertContains(response, 'data-copy-value="10.0.0.0/26"')
        self.assertContains(response, f'?subnet={plans_payload[0]["allocations"][0]["id"]}')

    def test_empty_dashboard_uses_explanatory_workflow_instead_of_fake_plan(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:user"))
        self.assertIsNone(response.context["resume_project"])
        self.assertEqual(response.context["resume_visualization"], [])
        self.assertContains(response, "From boundary to saved plan")
        self.assertNotContains(response, "Latest saved plan")
