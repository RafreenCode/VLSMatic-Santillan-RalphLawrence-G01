from ipaddress import IPv4Network

from django.test import TestCase

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import AllocationError, allocate_project, project_summary


class AllocationServiceTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("student", "student@example.com", "SafePassword!327")
        self.project = NetworkProject.objects.create(owner=user, name="Campus", base_network="192.168.10.0", prefix_length=24)

    def test_allocates_largest_requirement_first_and_persists_results(self):
        small = SubnetRequirement.objects.create(project=self.project, name="Printers", required_hosts=10, sort_order=0)
        large = SubnetRequirement.objects.create(project=self.project, name="Laboratory", required_hosts=100, sort_order=1)
        medium = SubnetRequirement.objects.create(project=self.project, name="Faculty", required_hosts=30, sort_order=2)

        allocate_project(self.project)
        self.assertEqual((large.allocation.network_address, large.allocation.prefix_length, large.allocation.usable_capacity), ("192.168.10.0", 25, 126))
        self.assertEqual((medium.allocation.network_address, medium.allocation.prefix_length), ("192.168.10.128", 27))
        self.assertEqual((small.allocation.network_address, small.allocation.prefix_length), ("192.168.10.160", 28))
        self.assertEqual(large.allocation.first_usable_address, "192.168.10.1")
        self.assertEqual(large.allocation.last_usable_address, "192.168.10.126")
        self.assertEqual(large.allocation.broadcast_address, "192.168.10.127")
        self.assertEqual(large.allocation.subnet_mask, "255.255.255.128")

    def test_allocations_do_not_overlap_and_stay_inside_base_network(self):
        for number, hosts in enumerate((60, 30, 12, 5), start=1):
            SubnetRequirement.objects.create(project=self.project, name=f"Subnet {number}", required_hosts=hosts)
        allocate_project(self.project)
        allocations = [IPv4Network(f"{item.allocation.network_address}/{item.allocation.prefix_length}") for item in self.project.requirements.all()]
        base = IPv4Network(self.project.cidr)
        self.assertTrue(all(item.subnet_of(base) for item in allocations))
        for index, allocation in enumerate(allocations):
            self.assertTrue(all(not allocation.overlaps(other) for other in allocations[index + 1 :]))

    def test_exact_fit_allocation(self):
        SubnetRequirement.objects.create(project=self.project, name="All hosts", required_hosts=254)
        allocate_project(self.project)
        requirement = self.project.requirements.get()
        self.assertEqual(requirement.allocation.network_address, "192.168.10.0")
        self.assertEqual(requirement.allocation.prefix_length, 24)

    def test_insufficient_capacity_does_not_partially_replace_results(self):
        first = SubnetRequirement.objects.create(project=self.project, name="First", required_hosts=100)
        second = SubnetRequirement.objects.create(project=self.project, name="Second", required_hosts=100)
        allocate_project(self.project)
        first.refresh_from_db()
        previous_run = self.project.calculation_run.pk
        previous_network = first.allocation.network_address
        second.required_hosts = 200
        second.save(update_fields=("required_hosts",))

        with self.assertRaises(AllocationError):
            allocate_project(self.project)

        self.project.refresh_from_db()
        first.refresh_from_db()
        self.assertEqual(self.project.calculation_run.pk, previous_run)
        self.assertEqual(first.allocation.network_address, previous_network)

    def test_empty_project_is_rejected(self):
        with self.assertRaisesMessage(AllocationError, "Add at least one"):
            allocate_project(self.project)

    def test_summary_reports_both_utilization_metrics(self):
        SubnetRequirement.objects.create(project=self.project, name="Lab", required_hosts=50)
        allocate_project(self.project)
        requirements = list(self.project.requirements.select_related("allocation"))
        summary = project_summary(self.project, requirements)
        self.assertEqual(summary["allocated_addresses"], 64)
        self.assertEqual(summary["remaining_addresses"], 192)
        self.assertAlmostEqual(summary["host_efficiency"], 50 / 62 * 100)
        self.assertEqual(summary["address_consumption"], 25)

    def test_thirty_prefix_exact_fit(self):
        project = NetworkProject.objects.create(owner=self.project.owner, name="Point to point", base_network="10.0.0.0", prefix_length=30)
        requirement = SubnetRequirement.objects.create(project=project, name="Link", required_hosts=2)
        allocate_project(project)
        self.assertEqual(requirement.allocation.prefix_length, 30)

