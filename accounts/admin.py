from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


admin.site.site_header = "VLSMatic administration"
admin.site.site_title = "VLSMatic administration"
admin.site.index_title = "Administration workspace"
admin.site.site_url = "/dashboard/"


@admin.register(User)
class VLSMaticUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("VLSMatic access", {"fields": ("role", "contact_number", "profile_photo_path")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("VLSMatic access", {"fields": ("email", "role", "contact_number", "profile_photo_path")}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("last_login", "date_joined")
