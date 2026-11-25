import secrets

from django.db import migrations, models
from django.utils.text import slugify


ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def backfill_project_slugs(apps, schema_editor):
    NetworkProject = apps.get_model("network_projects", "NetworkProject")
    used = set(NetworkProject.objects.exclude(slug__isnull=True).exclude(slug="").values_list("slug", flat=True))
    for project in NetworkProject.objects.all():
        if project.slug:
            continue
        base = slugify(project.name or "")[:96].strip("-") or "project"
        while True:
            token = "".join(secrets.choice(ALPHABET) for _ in range(6))
            candidate = f"{base}-{token}"
            if candidate not in used:
                used.add(candidate)
                project.slug = candidate
                project.save(update_fields=["slug"])
                break


class Migration(migrations.Migration):
    dependencies = [
        ("network_projects", "0003_remove_subnetrequirement_unique_subnet_name_per_project_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="networkproject",
            name="slug",
            field=models.SlugField(db_index=False, editable=False, max_length=150, null=True),
        ),
        migrations.RunPython(backfill_project_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="networkproject",
            name="slug",
            field=models.SlugField(db_index=True, editable=False, max_length=150, unique=True),
        ),
    ]
