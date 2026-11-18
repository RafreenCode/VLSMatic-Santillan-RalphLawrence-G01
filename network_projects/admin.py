from django.contrib import admin

from .models import NetworkProject, SubnetRequirement


class SubnetRequirementInline(admin.TabularInline):
    model = SubnetRequirement
    extra = 0


@admin.register(NetworkProject)
class NetworkProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "base_network", "prefix_length", "updated_at")
    list_filter = ("prefix_length",)
    search_fields = ("name", "owner__username", "owner__email")
    inlines = (SubnetRequirementInline,)

