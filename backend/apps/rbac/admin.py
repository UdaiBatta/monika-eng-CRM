from django.contrib import admin

from .models import Permission, PermissionOverride, Role, RoleAssignment, RolePermission

for model in (Permission, Role, RolePermission, RoleAssignment, PermissionOverride):
    admin.site.register(model)
