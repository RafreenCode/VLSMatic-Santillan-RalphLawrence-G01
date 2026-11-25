import secrets

from django.db import migrations, models
from django.utils.text import slugify


ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def backfill_group_slugs(apps, schema_editor):
    WorkspaceGroup = apps.get_model("accounts", "WorkspaceGroup")
    used = set(WorkspaceGroup.objects.exclude(slug__isnull=True).exclude(slug="").values_list("slug", flat=True))
    for group in WorkspaceGroup.objects.all():
        if group.slug:
            continue
        base = slugify(group.name or "")[:96].strip("-") or "group"
        while True:
            token = "".join(secrets.choice(ALPHABET) for _ in range(6))
            candidate = f"{base}-{token}"
            if candidate not in used:
                used.add(candidate)
                group.slug = candidate
                group.save(update_fields=["slug"])
                break


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_workspacegroup_groupmembership"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspacegroup",
            name="slug",
            field=models.SlugField(db_index=False, editable=False, max_length=150, null=True),
        ),
        migrations.RunPython(backfill_group_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="workspacegroup",
            name="slug",
            field=models.SlugField(db_index=True, editable=False, max_length=150, unique=True),
        ),
    ]
