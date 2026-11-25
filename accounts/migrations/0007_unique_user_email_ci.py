from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def normalize_emails(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    users = User.objects.using(schema_editor.connection.alias)
    duplicates = users.annotate(canonical=Lower(Trim("email"))).values("canonical").annotate(
        total=models.Count("pk")
    ).filter(total__gt=1)
    if duplicates.exists():
        raise RuntimeError(
            "Duplicate account emails exist after normalization. Resolve them with the account owners "
            "before rerunning this migration; no accounts have been changed."
        )
    users.update(email=Lower(Trim("email")))


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_workspacegroup_slug")]
    operations = [
        migrations.RunPython(normalize_emails, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
        ),
    ]
