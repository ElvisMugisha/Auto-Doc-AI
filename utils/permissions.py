from rest_framework import permissions
from utils import choices

class IsSuperAdminOrSuperUser(permissions.BasePermission):
    """
    Custom permission to only allow Super Admins or Superusers to access the view.
    """

    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is a superuser
        if request.user.is_superuser:
            return True

        # Check if user has the Super_Admin role
        if request.user.role == choices.UserRole.SUPER_ADMIN:
            return True

        return False
