from django.contrib import admin

from .models import User, Passcode


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_verified",
    )

    list_filter = (
        "role",
        "is_active",
        "is_verified",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    ordering = (
        "-created_at",
    )


@admin.register(Passcode)
class PasscodeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "code",
        "code_type",
        "created_at",
        "expires_at",
        "is_used",
    )

    list_filter = (
        "code_type",
        "is_used",
    )

    search_fields = (
        "user",
        "code",
        "code_type",
    )

    ordering = (
        "-created_at",
    )
