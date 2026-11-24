from django.contrib import admin

from .models import CalculationRun, NetworkProject, SubnetAllocation, SubnetRequirement


class SubnetRequirementInline(admin.TabularInline):
    model = SubnetRequirement
    extra = 0


@admin.register(NetworkProject)
class NetworkProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "base_network", "prefix_length", "updated_at")
    list_filter = ("prefix_length",)
    search_fields = ("name", "owner__username", "owner__email")
    inlines = (SubnetRequirementInline,)


class SubnetAllocationInline(admin.TabularInline):
    model = SubnetAllocation
    extra = 0
    readonly_fields = (
        "requirement", "network_address", "prefix_length", "subnet_mask",
        "first_usable_address", "last_usable_address", "broadcast_address", "allocated_addresses",
    )


@admin.register(CalculationRun)
class CalculationRunAdmin(admin.ModelAdmin):
    list_display = ("project", "generated_at")
    search_fields = ("project__name", "project__owner__username", "project__owner__email")
    inlines = (SubnetAllocationInline,)

