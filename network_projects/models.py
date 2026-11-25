from ipaddress import IPv4Network

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from accounts.models import generate_public_slug


class NetworkProject(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="network_projects",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, unique=True, db_index=True, editable=False)
    description = models.TextField(blank=True, max_length=1000)
    base_network = models.GenericIPAddressField(protocol="IPv4")
    prefix_length = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "name")
        indexes = [models.Index(fields=("owner", "updated_at"), name="project_owner_updated_idx")]
        constraints = [
            models.UniqueConstraint(Lower("name"), "owner", name="unique_project_name_per_owner_ci"),
            models.CheckConstraint(condition=models.Q(prefix_length__gte=0, prefix_length__lte=30), name="project_prefix_0_30"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.base_network and self.prefix_length is not None:
            try:
                IPv4Network(self.cidr, strict=True)
            except ValueError as error:
                raise ValidationError(
                    {"base_network": "Enter the network address for this prefix; host addresses are not accepted."}
                ) from error

    @classmethod
    def generate_unique_slug(cls, name: str) -> str:
        for _ in range(25):
            candidate = generate_public_slug(name, fallback="project")
            if not cls.objects.filter(slug=candidate).exists():
                return candidate
        raise RuntimeError("Could not generate a unique project slug.")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug(self.name)
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def cidr(self):
        return f"{self.base_network}/{self.prefix_length}"

    @property
    def has_allocations(self):
        return hasattr(self, "calculation_run")


class SubnetRequirement(models.Model):
    project = models.ForeignKey(
        NetworkProject,
        on_delete=models.CASCADE,
        related_name="requirements",
    )
    name = models.CharField(max_length=100)
    required_hosts = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(Lower("name"), "project", name="unique_subnet_name_per_project_ci"),
            models.CheckConstraint(condition=models.Q(required_hosts__gte=1), name="required_hosts_at_least_one"),
        ]
        indexes = [models.Index(fields=("project", "sort_order"), name="requirement_project_order_idx")]

    def __str__(self):
        return f"{self.name} ({self.required_hosts} hosts)"

    @property
    def current_allocation(self):
        try:
            return self.allocation
        except SubnetAllocation.DoesNotExist:
            return None


class CalculationRun(models.Model):
    project = models.OneToOneField(
        NetworkProject, on_delete=models.CASCADE, related_name="calculation_run"
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Current plan for {self.project}"


class SubnetAllocation(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.CASCADE, related_name="allocations")
    requirement = models.OneToOneField(
        SubnetRequirement, on_delete=models.CASCADE, related_name="allocation"
    )
    network_address = models.GenericIPAddressField(protocol="IPv4")
    prefix_length = models.PositiveSmallIntegerField()
    subnet_mask = models.GenericIPAddressField(protocol="IPv4")
    first_usable_address = models.GenericIPAddressField(protocol="IPv4")
    last_usable_address = models.GenericIPAddressField(protocol="IPv4")
    broadcast_address = models.GenericIPAddressField(protocol="IPv4")
    allocated_addresses = models.PositiveBigIntegerField()

    class Meta:
        ordering = ("network_address",)
        constraints = [
            models.CheckConstraint(condition=models.Q(prefix_length__gte=0, prefix_length__lte=30), name="allocation_prefix_0_30"),
            models.CheckConstraint(condition=models.Q(allocated_addresses__gte=4), name="allocation_minimum_four_addresses"),
        ]

    @property
    def usable_capacity(self):
        return self.allocated_addresses - 2

    def clean(self):
        super().clean()
        if self.run_id and self.requirement_id and self.run.project_id != self.requirement.project_id:
            raise ValidationError("The allocation, requirement, and calculation run must belong to the same project.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

