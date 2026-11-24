from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from network_projects.models import CalculationRun, NetworkProject, SubnetAllocation, SubnetRequirement


class NetworkProjectModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("student", "student@example.com", "SafePassword!327")
        self.project = NetworkProject.objects.create(
            owner=self.user,
            name="Laboratory plan",
            base_network="192.168.10.0",
            prefix_length=24,
        )

    def test_project_belongs_to_user_and_exposes_cidr(self):
        self.assertEqual(self.project.owner, self.user)
        self.assertEqual(self.project.cidr, "192.168.10.0/24")

    def test_requirement_cascade_deletes_with_project(self):
        SubnetRequirement.objects.create(project=self.project, name="Lab A", required_hosts=30)
        self.project.delete()
        self.assertFalse(SubnetRequirement.objects.exists())

    def test_subnet_names_are_unique_per_project(self):
        SubnetRequirement.objects.create(project=self.project, name="Lab A", required_hosts=30)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SubnetRequirement.objects.create(project=self.project, name="Lab A", required_hosts=20)

    def test_required_hosts_database_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SubnetRequirement.objects.create(project=self.project, name="Invalid", required_hosts=0)

    def test_project_names_are_unique_per_owner_case_insensitively(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            NetworkProject.objects.create(owner=self.user, name="laboratory PLAN", base_network="10.0.0.0", prefix_length=8)

    def test_run_and_allocations_cascade_with_project(self):
        requirement = SubnetRequirement.objects.create(project=self.project, name="Lab", required_hosts=10)
        run = CalculationRun.objects.create(project=self.project)
        SubnetAllocation.objects.create(run=run, requirement=requirement, network_address="192.168.10.0", prefix_length=28, subnet_mask="255.255.255.240", first_usable_address="192.168.10.1", last_usable_address="192.168.10.14", broadcast_address="192.168.10.15", allocated_addresses=16)
        self.project.delete()
        self.assertFalse(CalculationRun.objects.exists())
        self.assertFalse(SubnetAllocation.objects.exists())

