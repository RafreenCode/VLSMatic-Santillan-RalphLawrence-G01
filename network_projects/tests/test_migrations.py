from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class SDDDataMigrationTests(TransactionTestCase):
    migrate_from = [("accounts", "0002_user_profile_photo_path"), ("network_projects", "0001_initial")]
    migrate_to = [("accounts", "0004_role_role_code_user_or_admin"), ("network_projects", "0003_remove_subnetrequirement_unique_subnet_name_per_project_and_more")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        User = old_apps.get_model("accounts", "User")
        Project = old_apps.get_model("network_projects", "NetworkProject")
        Requirement = old_apps.get_model("network_projects", "SubnetRequirement")

        admin = User.objects.create(username="legacy-admin", email="admin@example.com", password="hash", role="admin")
        user = User.objects.create(username="legacy-user", email="user@example.com", password="hash", role="user")
        project = Project.objects.create(owner=user, name="Legacy plan", base_network="192.168.50.0", prefix_length=24)
        Requirement.objects.create(
            project=project,
            name="Allocated",
            required_hosts=50,
            sort_order=0,
            network_address="192.168.50.0",
            prefix_length=26,
            subnet_mask="255.255.255.192",
            first_usable_address="192.168.50.1",
            last_usable_address="192.168.50.62",
            broadcast_address="192.168.50.63",
            allocated_capacity=62,
        )
        Requirement.objects.create(project=project, name="Draft", required_hosts=10, sort_order=1)
        self.legacy_ids = {"admin": admin.pk, "user": user.pk, "project": project.pk}

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.apps = executor.loader.project_state(self.migrate_to).apps

    def test_existing_roles_and_allocations_are_preserved(self):
        User = self.apps.get_model("accounts", "User")
        Role = self.apps.get_model("accounts", "Role")
        Project = self.apps.get_model("network_projects", "NetworkProject")
        Requirement = self.apps.get_model("network_projects", "SubnetRequirement")
        Run = self.apps.get_model("network_projects", "CalculationRun")
        Allocation = self.apps.get_model("network_projects", "SubnetAllocation")

        self.assertEqual(set(Role.objects.values_list("code", flat=True)), {"user", "admin"})
        self.assertEqual(User.objects.get(pk=self.legacy_ids["admin"]).role_record_id, "admin")
        self.assertEqual(User.objects.get(pk=self.legacy_ids["user"]).role_record_id, "user")
        self.assertTrue(Project.objects.filter(pk=self.legacy_ids["project"]).exists())
        self.assertEqual(Requirement.objects.count(), 2)
        self.assertEqual(Run.objects.count(), 1)
        allocation = Allocation.objects.get()
        self.assertEqual(allocation.network_address, "192.168.50.0")
        self.assertEqual(allocation.allocated_addresses, 64)
        self.assertFalse(Allocation.objects.filter(requirement__name="Draft").exists())
