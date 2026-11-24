from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from accounts.models import User
from network_projects.models import CalculationRun, NetworkProject, SubnetAllocation, SubnetRequirement
from network_projects.services import allocate_project


class AllocationConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_recalculations_leave_one_complete_plan(self):
        user = User.objects.create_user("concurrent", "concurrent@example.com", "SafePassword!327")
        project = NetworkProject.objects.create(owner=user, name="Concurrent", base_network="10.20.0.0", prefix_length=24)
        SubnetRequirement.objects.create(project=project, name="Large", required_hosts=100)
        SubnetRequirement.objects.create(project=project, name="Small", required_hosts=20)

        def recalculate():
            close_old_connections()
            try:
                allocate_project(NetworkProject.objects.get(pk=project.pk))
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(recalculate) for _ in range(2)]
            for future in futures:
                future.result()

        self.assertEqual(CalculationRun.objects.filter(project=project).count(), 1)
        run = CalculationRun.objects.get(project=project)
        self.assertEqual(SubnetAllocation.objects.filter(run=run).count(), 2)
        self.assertEqual(SubnetAllocation.objects.filter(requirement__project=project).count(), 2)
