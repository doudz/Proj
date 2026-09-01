from rest_framework import permissions

from apps.workspaces.models import Membership


class IsWorkspaceMember(permissions.BasePermission):
    """Grants access to any member of the workspace referenced by the view."""

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, "workspace", obj)
        return Membership.objects.filter(workspace=workspace, user=request.user).exists()


class IsWorkspaceAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, "workspace", obj)
        return Membership.objects.filter(
            workspace=workspace, user=request.user, role__in=[Membership.Role.OWNER, Membership.Role.ADMIN]
        ).exists()


def user_workspace_ids(user):
    return Membership.objects.filter(user=user).values_list("workspace_id", flat=True)
