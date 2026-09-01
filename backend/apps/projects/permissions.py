from rest_framework.exceptions import PermissionDenied

from apps.projects.models import ProjectMembership
from apps.workspaces.models import Membership

# Fields a "member" is allowed to change on a task they are assigned to -
# this is the whole point of that role: change the *state* of their own
# work (status, progress, real start/finish, the custom fields the project
# asks them to fill in), nothing structural (title, planned dates and
# duration, dependencies, assignment...).
MEMBER_EDITABLE_TASK_FIELDS = {
    "progress",
    "column",
    "actual_start_date",
    "actual_end_date",
    "custom_field_values",
}


def get_project_role(user, project):
    """Effective role of `user` on `project`.

    Workspace owners/admins implicitly administer every project in their
    workspace (consistent with them already administering the whole
    workspace) without needing an explicit ProjectMembership row. Everyone
    else falls back to their ProjectMembership role, defaulting to
    'viewer' (read-only) when they have no explicit role on this project.
    """
    ws_membership = Membership.objects.filter(workspace_id=project.workspace_id, user=user).first()
    if ws_membership and ws_membership.role in (Membership.Role.OWNER, Membership.Role.ADMIN):
        return ProjectMembership.Role.ADMIN
    pm = ProjectMembership.objects.filter(project=project, user=user).first()
    return pm.role if pm else ProjectMembership.Role.VIEWER


def is_project_admin(user, project):
    return get_project_role(user, project) == ProjectMembership.Role.ADMIN


def can_manage_project(user, project):
    """Structural changes: project settings, columns, labels, tasks (create/
    delete/full edit), dependencies, baseline, members, external contacts."""
    return is_project_admin(user, project)


def can_edit_task_state(user, task):
    """Can this user change progress/column (and use the start/complete
    actions) on this specific task? True for admins always, for members only
    on tasks they are personally assigned to, never for viewers."""
    role = get_project_role(user, task.project)
    if role == ProjectMembership.Role.ADMIN:
        return True
    if role == ProjectMembership.Role.MEMBER:
        return task.assignees.filter(pk=user.pk).exists()
    return False


def can_comment(user, project):
    """Admins and members may discuss project work; viewers are strictly
    read-only ("rien faire d'autre")."""
    return get_project_role(user, project) in (ProjectMembership.Role.ADMIN, ProjectMembership.Role.MEMBER)


def require_project_admin(user, project):
    if not is_project_admin(user, project):
        raise PermissionDenied("Seuls les administrateurs du projet peuvent effectuer cette action.")


def require_comment_permission(user, project):
    if not can_comment(user, project):
        raise PermissionDenied("Les observateurs ne peuvent pas commenter.")


def require_task_state_permission(user, task, changed_fields):
    """Raise unless the user may apply `changed_fields` to `task`: admins can
    change anything, members only the state fields of tasks assigned to them."""
    role = get_project_role(user, task.project)
    if role == ProjectMembership.Role.ADMIN:
        return
    if role == ProjectMembership.Role.MEMBER and task.assignees.filter(pk=user.pk).exists():
        disallowed = set(changed_fields) - MEMBER_EDITABLE_TASK_FIELDS
        if not disallowed:
            return
        raise PermissionDenied(
            "En tant que membre, vous ne pouvez modifier que l'avancement et le statut de vos propres taches."
        )
    raise PermissionDenied("Vous n'avez pas la permission de modifier cette tache.")
