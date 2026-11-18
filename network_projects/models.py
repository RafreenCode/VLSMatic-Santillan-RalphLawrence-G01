from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class NetworkProject(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="network_projects",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=1000)
    base_network = models.GenericIPAddressField(protocol="IPv4")
    prefix_length = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "name")
        indexes = [models.Index(fields=("owner", "updated_at"), name="project_owner_updated_idx")]

    def __str__(self):
        return self.name

    @property
    def cidr(self):
        return f"{self.base_network}/{self.prefix_length}"

    @property
    def has_allocations(self):
        return self.requirements.filter(network_address__isnull=False).exists()


class SubnetRequirement(models.Model):
    project = models.ForeignKey(
        NetworkProject,
        on_delete=models.CASCADE,
        related_name="requirements",
    )
    name = models.CharField(max_length=100)
    required_hosts = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    sort_order = models.PositiveIntegerField(default=0)
    network_address = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    prefix_length = models.PositiveSmallIntegerField(null=True, blank=True)
    subnet_mask = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    first_usable_address = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    last_usable_address = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    broadcast_address = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    allocated_capacity = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(fields=("project", "name"), name="unique_subnet_name_per_project"),
            models.CheckConstraint(condition=models.Q(required_hosts__gte=1), name="required_hosts_at_least_one"),
        ]
        indexes = [models.Index(fields=("project", "sort_order"), name="requirement_project_order_idx")]

    def __str__(self):
        return f"{self.name} ({self.required_hosts} hosts)"

    def clear_allocation(self):
        for field in self.allocation_fields():
            setattr(self, field, None)

    @staticmethod
    def allocation_fields():
        return (
            "network_address",
            "prefix_length",
            "subnet_mask",
            "first_usable_address",
            "last_usable_address",
            "broadcast_address",
            "allocated_capacity",
        )

