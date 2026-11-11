from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = "Assign the VLSMatic Administrator role to an existing account."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError("No account exists with that username.") from exc

        user.role = User.Role.ADMIN
        user.is_staff = True
        user.save(update_fields=["role", "is_staff"])
        self.stdout.write(self.style.SUCCESS(f"{user.username} is now a VLSMatic administrator."))
