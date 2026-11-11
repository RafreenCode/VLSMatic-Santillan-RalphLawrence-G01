from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class VLSMaticUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("VLSMatic access", {"fields": ("role", "contact_number")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("VLSMatic access", {"fields": ("email", "role", "contact_number")}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = UserAdmin.list_filter + ("role",)
