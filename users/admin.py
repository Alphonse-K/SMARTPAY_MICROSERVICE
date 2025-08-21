from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    # Fields to display in the admin list view
    list_display = ("username", "email", "is_active", "is_staff", "is_superuser", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")

    # Fields shown when editing a user
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login",)}),  # 🚨 no date_joined here
    )

    # Fields shown when creating a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "is_active", "is_staff", "is_superuser"),
        }),
    )

    search_fields = ("username", "email")
    ordering = ("-date_joined",)
