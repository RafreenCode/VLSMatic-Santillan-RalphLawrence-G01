import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


def migrate_current_allocations(apps, schema_editor):
    Requirement = apps.get_model("network_projects", "SubnetRequirement")
    Run = apps.get_model("network_projects", "CalculationRun")
    Allocation = apps.get_model("network_projects", "SubnetAllocation")
    runs = {}
    for requirement in Requirement.objects.exclude(network_address__isnull=True).iterator():
        run = runs.get(requirement.project_id)
        if run is None:
            run = Run.objects.create(project_id=requirement.project_id)
            runs[requirement.project_id] = run
        Allocation.objects.create(
            run=run,
            requirement=requirement,
            network_address=requirement.network_address,
            prefix_length=requirement.prefix_length,
            subnet_mask=requirement.subnet_mask,
            first_usable_address=requirement.first_usable_address,
            last_usable_address=requirement.last_usable_address,
            broadcast_address=requirement.broadcast_address,
            allocated_addresses=requirement.allocated_capacity + 2,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("network_projects", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CalculationRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="calculation_run", to="network_projects.networkproject")),
            ],
        ),
        migrations.CreateModel(
            name="SubnetAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("network_address", models.GenericIPAddressField(protocol="IPv4")),
                ("prefix_length", models.PositiveSmallIntegerField()),
                ("subnet_mask", models.GenericIPAddressField(protocol="IPv4")),
                ("first_usable_address", models.GenericIPAddressField(protocol="IPv4")),
                ("last_usable_address", models.GenericIPAddressField(protocol="IPv4")),
                ("broadcast_address", models.GenericIPAddressField(protocol="IPv4")),
                ("allocated_addresses", models.PositiveBigIntegerField()),
                ("requirement", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="allocation", to="network_projects.subnetrequirement")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="allocations", to="network_projects.calculationrun")),
            ],
            options={"ordering": ("network_address",)},
        ),
        migrations.RunPython(migrate_current_allocations, migrations.RunPython.noop),
        migrations.RemoveField(model_name="subnetrequirement", name="allocated_capacity"),
        migrations.RemoveField(model_name="subnetrequirement", name="broadcast_address"),
        migrations.RemoveField(model_name="subnetrequirement", name="first_usable_address"),
        migrations.RemoveField(model_name="subnetrequirement", name="last_usable_address"),
        migrations.RemoveField(model_name="subnetrequirement", name="network_address"),
        migrations.RemoveField(model_name="subnetrequirement", name="prefix_length"),
        migrations.RemoveField(model_name="subnetrequirement", name="subnet_mask"),
        migrations.AddConstraint(model_name="networkproject", constraint=models.UniqueConstraint(django.db.models.functions.text.Lower("name"), models.F("owner"), name="unique_project_name_per_owner_ci")),
        migrations.AddConstraint(model_name="networkproject", constraint=models.CheckConstraint(condition=models.Q(prefix_length__gte=0, prefix_length__lte=30), name="project_prefix_0_30")),
        migrations.AddConstraint(model_name="subnetallocation", constraint=models.CheckConstraint(condition=models.Q(prefix_length__gte=0, prefix_length__lte=30), name="allocation_prefix_0_30")),
        migrations.AddConstraint(model_name="subnetallocation", constraint=models.CheckConstraint(condition=models.Q(allocated_addresses__gte=4), name="allocation_minimum_four_addresses")),
    ]
