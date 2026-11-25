from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import allocate_project


class SubmissionIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("planner", "planner@example.com", "SafePassword!327")
        cls.project = NetworkProject.objects.create(owner=cls.user, name="Campus", base_network="10.0.0.0", prefix_length=24)

    def setUp(self):
        self.client.force_login(self.user)

    def test_repeated_project_submission_creates_only_one_record(self):
        data = {"name": "Branch", "base_network": "10.1.0.0", "prefix_length": 24}
        url = reverse("network_projects:create")
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertContains(self.client.post(url, data), "already have a project")
        self.assertEqual(NetworkProject.objects.filter(owner=self.user, name="Branch").count(), 1)

    def test_repeated_subnet_submission_keeps_one_complete_plan(self):
        url = reverse("network_projects:requirement_create", args=[self.project.slug])
        data = {"name": "Lab", "required_hosts": 50}
        self.client.post(url, data)
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "already has a subnet")
        self.assertEqual(self.project.requirements.count(), 1)
        self.assertEqual(self.project.calculation_run.allocations.count(), 1)

    def test_boundary_failure_restores_project_and_previous_allocation(self):
        SubnetRequirement.objects.create(project=self.project, name="Lab", required_hosts=100)
        allocate_project(self.project)
        run_id = self.project.calculation_run.pk
        response = self.client.post(reverse("network_projects:update", args=[self.project.slug]), {
            "name": "Campus", "base_network": "10.0.0.0", "prefix_length": 30,
        }, follow=True)
        self.assertContains(response, "exceed this network")
        self.project.refresh_from_db()
        self.assertEqual(self.project.prefix_length, 24)
        self.assertEqual(self.project.calculation_run.pk, run_id)

    def test_save_time_validation_is_shown_without_creating_bad_record(self):
        with patch("network_projects.models.NetworkProject.save", side_effect=ValidationError("Name was just taken.")):
            response = self.client.post(reverse("network_projects:create"), {
                "name": "Conflicting", "base_network": "10.1.0.0", "prefix_length": 24,
            })
        self.assertContains(response, "Name was just taken.")
        self.assertFalse(NetworkProject.objects.filter(name="Conflicting").exists())

    def test_unrelated_database_integrity_errors_are_not_hidden(self):
        with patch("network_projects.models.NetworkProject.save", side_effect=IntegrityError("unexpected constraint")):
            with self.assertRaises(IntegrityError):
                self.client.post(reverse("network_projects:create"), {
                    "name": "Unexpected", "base_network": "10.1.0.0", "prefix_length": 24,
                })

    def test_user_supplied_markup_is_escaped_in_project_and_studio(self):
        self.project.name = '<script>alert("project")</script>'
        self.project.description = '<img src=x onerror=alert("description")>'
        self.project.save()
        SubnetRequirement.objects.create(project=self.project, name='<script>alert("subnet")</script>', required_hosts=10)
        allocate_project(self.project)
        response = self.client.get(reverse("network_projects:detail", args=[self.project.slug]))
        self.assertNotContains(response, '<script>alert("project")</script>')
        self.assertNotContains(response, '<img src=x onerror=alert("description")>')
        self.assertNotContains(response, '<script>alert("subnet")</script>')
