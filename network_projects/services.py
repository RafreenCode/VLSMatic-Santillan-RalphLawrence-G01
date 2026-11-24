from ipaddress import IPv4Address, IPv4Network
from math import ceil, log2

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import CalculationRun, NetworkProject, SubnetAllocation


class AllocationError(ValidationError):
    pass


def _block_size(required_hosts):
    return 2 ** ceil(log2(required_hosts + 2))


@transaction.atomic
def allocate_project(project, allow_empty=False):
    project = NetworkProject.objects.select_for_update().get(pk=project.pk)
    requirements = list(
        project.requirements.select_for_update().order_by("-required_hosts", "sort_order", "id")
    )
    if not requirements:
        if allow_empty:
            CalculationRun.objects.filter(project=project).delete()
            return []
        raise AllocationError("Add at least one subnet requirement before generating an allocation.")

    base = IPv4Network(project.cidr, strict=True)
    cursor = int(base.network_address)
    final_address = int(base.broadcast_address)
    planned = []

    for requirement in requirements:
        size = _block_size(requirement.required_hosts)
        prefix = 32 - int(log2(size))
        aligned_start = ((cursor + size - 1) // size) * size
        aligned_end = aligned_start + size - 1
        if aligned_end > final_address:
            raise AllocationError(
                "The subnet requirements exceed this network's capacity. Increase the network size or reduce the host requirements."
            )
        subnet = IPv4Network((IPv4Address(aligned_start), prefix), strict=True)
        if not subnet.subnet_of(base):
            raise AllocationError("A subnet would fall outside the selected base network.")
        planned.append((requirement, subnet))
        cursor = aligned_end + 1

    CalculationRun.objects.filter(project=project).delete()
    run = CalculationRun.objects.create(project=project)
    allocations = []
    for requirement, subnet in planned:
        allocations.append(
            SubnetAllocation(
                run=run,
                requirement=requirement,
                network_address=str(subnet.network_address),
                prefix_length=subnet.prefixlen,
                subnet_mask=str(subnet.netmask),
                first_usable_address=str(subnet.network_address + 1),
                last_usable_address=str(subnet.broadcast_address - 1),
                broadcast_address=str(subnet.broadcast_address),
                allocated_addresses=subnet.num_addresses,
            )
        )
    SubnetAllocation.objects.bulk_create(allocations)
    return allocations


def project_summary(project, requirements):
    total_addresses = 2 ** (32 - project.prefix_length)
    total_required = sum(item.required_hosts for item in requirements)
    allocations = [item.current_allocation for item in requirements]
    allocations = [item for item in allocations if item is not None]
    allocated_addresses = sum(item.allocated_addresses for item in allocations)
    usable_capacity = sum(item.usable_capacity for item in allocations)
    return {
        "subnet_count": len(requirements),
        "total_required_hosts": total_required,
        "allocated_addresses": allocated_addresses,
        "remaining_addresses": total_addresses - allocated_addresses,
        "host_efficiency": (total_required / usable_capacity * 100) if usable_capacity else 0,
        "address_consumption": (allocated_addresses / total_addresses * 100) if total_addresses else 0,
        "total_addresses": total_addresses,
    }
