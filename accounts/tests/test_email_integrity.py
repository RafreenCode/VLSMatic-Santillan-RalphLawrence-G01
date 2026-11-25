from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from dashboard.forms import AdminUserCreateForm, AdminUserUpdateForm


class EmailIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("existing", "existing@example.com", "SafePassword!327")

    def test_model_save_normalizes_email(self):
        user = User.objects.create_user("mixed", " Mixed@Example.COM ", "SafePassword!327")
        self.assertEqual(user.email, "mixed@example.com")

    def test_database_blocks_case_variant_even_when_save_is_bypassed(self):
        other = User.objects.create_user("other", "other@example.com", "SafePassword!327")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=other.pk).update(email="EXISTING@example.com")

    def test_admin_create_rejects_case_variant_email(self):
        form = AdminUserCreateForm(data={"username": "new", "email": "EXISTING@example.com", "role_record": "user", "password1": "SafePassword!327", "password2": "SafePassword!327"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_admin_update_rejects_case_variant_email(self):
        other = User.objects.create_user("other", "other@example.com", "SafePassword!327")
        form = AdminUserUpdateForm(instance=other, data={"email": "EXISTING@example.com", "role_record": "user"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
