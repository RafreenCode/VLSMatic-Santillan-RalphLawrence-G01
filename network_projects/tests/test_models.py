from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement


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

