from django.conf import settings
from django.db import models

from apps.workspaces.models import Workspace


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planifie"
        ACTIVE = "active", "En cours"
        ON_HOLD = "on_hold", "En pause"
        DONE = "done", "Termine"
        ARCHIVED = "archived", "Archive"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#42A5F5")
    icon = models.CharField(max_length=32, default="mdi-rocket-launch-outline")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    baseline_captured_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="projects_created")
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="ProjectMembership", related_name="projects", blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ProjectMembership(models.Model):
    """A user's role on a specific project.

    Workspace owners/admins implicitly get admin rights on every project in
    their workspace (see apps.projects.permissions.get_project_role) without
    needing a row here; this table is what governs everyone else:
      - admin: full control (structure, tasks, members, dependencies...)
      - member: can only change the state (progress/status/actual dates) of
        tasks they are assigned to, and comment on tasks
      - viewer: read-only, no exceptions

    A workspace member with no row here defaults to viewer for that project.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        MEMBER = "member", "Membre"
        VIEWER = "viewer", "Observateur"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")
        ordering = ["-role", "added_at"]

    def __str__(self):
        return f"{self.user} @ {self.project} ({self.role})"


class BoardColumn(models.Model):
    """A Kanban status column, also used to derive default task status colors."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=80)
    color = models.CharField(max_length=7, default="#90A4AE")
    order = models.PositiveIntegerField(default=0)
    is_done_column = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.project.name} / {self.name}"


class Label(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=60)
    color = models.CharField(max_length=7, default="#7E57C2")

    class Meta:
        unique_together = ("project", "name")

    def __str__(self):
        return self.name


DEFAULT_COLUMNS = [
    {"name": "A faire", "color": "#90A4AE", "order": 0, "is_done_column": False},
    {"name": "En cours", "color": "#42A5F5", "order": 1, "is_done_column": False},
    {"name": "En revue", "color": "#FFA726", "order": 2, "is_done_column": False},
    {"name": "Termine", "color": "#66BB6A", "order": 3, "is_done_column": True},
]
