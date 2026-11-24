import django.db.models.deletion
from django.db import migrations, models


def seed_and_map_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    User = apps.get_model("accounts", "User")
    Role.objects.bulk_create([
        Role(code="user", name="Regular User"),
        Role(code="admin", name="Administrator"),
    ])
    for user in User.objects.all().iterator():
        user.role_record_id = user.role_legacy
        user.save(update_fields=("role_record",))


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_profile_photo_path")]

    operations = [
        migrations.RenameField(model_name="user", old_name="role", new_name="role_legacy"),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("code", models.CharField(max_length=10, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=50)),
            ],
            options={"ordering": ("code",)},
        ),
        migrations.AddField(
            model_name="user",
            name="role_record",
            field=models.ForeignKey(db_column="role_code", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="users", to="accounts.role"),
        ),
        migrations.RunPython(seed_and_map_roles, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="role_legacy"),
        migrations.AlterField(
            model_name="user",
            name="role_record",
            field=models.ForeignKey(db_column="role_code", default="user", on_delete=django.db.models.deletion.PROTECT, related_name="users", to="accounts.role"),
        ),
    ]
