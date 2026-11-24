from django.test import TestCase

from accounts.models import User
from network_projects.forms import NetworkProjectForm, SubnetRequirementForm
from network_projects.models import NetworkProject, SubnetRequirement


class NetworkProjectFormTests(TestCase):
    def test_accepts_valid_ipv4_network(self):
        form = NetworkProjectForm(data={"name": "Campus", "description": "", "base_network": "10.10.0.0", "prefix_length": 16})
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_host_address_as_network_boundary(self):
        form = NetworkProjectForm(data={"name": "Campus", "description": "", "base_network": "192.168.1.5", "prefix_length": 24})
        self.assertFalse(form.is_valid())
        self.assertIn("base_network", form.errors)

    def test_rejects_ipv6_and_unsupported_prefix(self):
        form = NetworkProjectForm(data={"name": "Campus", "description": "", "base_network": "2001:db8::", "prefix_length": 31})
        self.assertFalse(form.is_valid())
        self.assertIn("base_network", form.errors)
        self.assertIn("prefix_length", form.errors)

    def test_accepts_zero_prefix(self):
        form = NetworkProjectForm(data={"name": "Internet", "description": "", "base_network": "0.0.0.0", "prefix_length": 0})
        self.assertTrue(form.is_valid(), form.errors)


class SubnetRequirementFormTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("student", "student@example.com", "SafePassword!327")
        self.project = NetworkProject.objects.create(owner=user, name="Campus", base_network="192.168.1.0", prefix_length=24)

    def test_rejects_duplicate_name_case_insensitively(self):
        SubnetRequirement.objects.create(project=self.project, name="Laboratory", required_hosts=30)
        form = SubnetRequirementForm(data={"name": "laboratory", "required_hosts": 20}, project=self.project)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_rejects_requirement_larger_than_project(self):
        form = SubnetRequirementForm(data={"name": "Oversized", "required_hosts": 300}, project=self.project)
        self.assertFalse(form.is_valid())
        self.assertIn("required_hosts", form.errors)

    def test_accepts_positive_host_requirement(self):
        form = SubnetRequirementForm(data={"name": "Laboratory", "required_hosts": 50}, project=self.project)
        self.assertTrue(form.is_valid(), form.errors)

