from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Role


class RoleModelTests(TestCase):
    def test_database_rejects_roles_outside_sdd_codes(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Role.objects.create(code="teacher", name="Teacher")
