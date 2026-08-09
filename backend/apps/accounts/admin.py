from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class MonikaUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "username", "is_active", "is_staff")
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
