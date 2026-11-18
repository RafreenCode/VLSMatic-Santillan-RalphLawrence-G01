from ipaddress import IPv4Network

from django.test import TestCase

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement
from network_projects.services import AllocationError, allocate_project


class AllocationServiceTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("student", "student@example.com", "SafePassword!327")
        self.project = NetworkProject.objects.create(owner=user, name="Campus", base_network="192.168.10.0", prefix_length=24)

    def test_allocates_largest_requirement_first_and_persists_results(self):
        small = SubnetRequirement.objects.create(project=self.project, name="Printers", required_hosts=10, sort_order=0)
        large = SubnetRequirement.objects.create(project=self.project, name="Laboratory", required_hosts=100, sort_order=1)
        medium = SubnetRequirement.objects.create(project=self.project, name="Faculty", required_hosts=30, sort_order=2)

        allocate_project(self.project)
        for requirement in (small, large, medium):
            requirement.refresh_from_db()

        self.assertEqual((large.network_address, large.prefix_length, large.allocated_capacity), ("192.168.10.0", 25, 126))
        self.assertEqual((medium.network_address, medium.prefix_length), ("192.168.10.128", 27))
        self.assertEqual((small.network_address, small.prefix_length), ("192.168.10.160", 28))
        self.assertEqual(large.first_usable_address, "192.168.10.1")
        self.assertEqual(large.last_usable_address, "192.168.10.126")
        self.assertEqual(large.broadcast_address, "192.168.10.127")
        self.assertEqual(large.subnet_mask, "255.255.255.128")

    def test_allocations_do_not_overlap_and_stay_inside_base_network(self):
        for number, hosts in enumerate((60, 30, 12, 5), start=1):
            SubnetRequirement.objects.create(project=self.project, name=f"Subnet {number}", required_hosts=hosts)
        allocate_project(self.project)
        allocations = [IPv4Network(f"{item.network_address}/{item.prefix_length}") for item in self.project.requirements.all()]
        base = IPv4Network(self.project.cidr)
        self.assertTrue(all(item.subnet_of(base) for item in allocations))
        for index, allocation in enumerate(allocations):
            self.assertTrue(all(not allocation.overlaps(other) for other in allocations[index + 1 :]))

    def test_exact_fit_allocation(self):
        SubnetRequirement.objects.create(project=self.project, name="All hosts", required_hosts=254)
        allocate_project(self.project)
        requirement = self.project.requirements.get()
        self.assertEqual(requirement.network_address, "192.168.10.0")
        self.assertEqual(requirement.prefix_length, 24)

    def test_insufficient_capacity_does_not_partially_replace_results(self):
        first = SubnetRequirement.objects.create(project=self.project, name="First", required_hosts=100)
        second = SubnetRequirement.objects.create(project=self.project, name="Second", required_hosts=100)
        allocate_project(self.project)
        first.refresh_from_db()
        previous_network = first.network_address
        second.required_hosts = 200
        second.save(update_fields=("required_hosts",))

        with self.assertRaises(AllocationError):
            allocate_project(self.project)

        first.refresh_from_db()
        self.assertEqual(first.network_address, previous_network)

    def test_empty_project_is_rejected(self):
        with self.assertRaisesMessage(AllocationError, "Add at least one"):
            allocate_project(self.project)

