from ipaddress import IPv4Address, IPv4Network
from math import ceil, log2

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import SubnetRequirement


class AllocationError(ValidationError):
    pass


def _block_size(required_hosts):
    return 2 ** ceil(log2(required_hosts + 2))


@transaction.atomic
def allocate_project(project):
    requirements = list(
        project.requirements.select_for_update().order_by("-required_hosts", "sort_order", "id")
    )
    if not requirements:
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

    for requirement, subnet in planned:
        requirement.network_address = str(subnet.network_address)
        requirement.prefix_length = subnet.prefixlen
        requirement.subnet_mask = str(subnet.netmask)
        requirement.first_usable_address = str(subnet.network_address + 1)
        requirement.last_usable_address = str(subnet.broadcast_address - 1)
        requirement.broadcast_address = str(subnet.broadcast_address)
        requirement.allocated_capacity = subnet.num_addresses - 2
        requirement.save(update_fields=SubnetRequirement.allocation_fields())

    return requirements

