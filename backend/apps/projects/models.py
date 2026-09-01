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
    # A template is a reusable blueprint: it never shows up in the normal project
    # lists and is only used to spawn real projects (see ProjectViewSet.instantiate).
    is_template = models.BooleanField(default=False)
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


class CustomField(models.Model):
    """A user-defined field added to every task of a project.

    The project owns the definition; the value for a given task lives in
    apps.tasks.models.CustomFieldValue. Values are always stored as text and
    interpreted according to `field_type` - that keeps a single storage shape
    while still letting the UI render the right editor and the search filter
    on them.
    """

    class FieldType(models.TextChoices):
        TEXT = "text", "Texte"
        NUMBER = "number", "Nombre"
        DATE = "date", "Date"
        SELECT = "select", "Liste de choix"
        CHECKBOX = "checkbox", "Case a cocher"
        URL = "url", "Lien"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="custom_fields")
    name = models.CharField(max_length=80)
    field_type = models.CharField(max_length=10, choices=FieldType.choices, default=FieldType.TEXT)
    # Choices for the "select" type, ignored otherwise.
    options = models.JSONField(default=list, blank=True)
    order = models.PositiveIntegerField(default=0)
    # When true the field gets its own column in the task list view.
    show_in_list = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("project", "name")

    def __str__(self):
        return f"{self.project.name} / {self.name}"


class AutomationRule(models.Model):
    """A "when X happens, do Y" rule scoped to a project.

    Kept deliberately small (one trigger, one action) rather than a general
    condition/action builder - chaining several simple rules together already
    covers most real workflows, and each rule stays easy to read at a glance.
    """

    class Trigger(models.TextChoices):
        TASK_CREATED = "task_created", "Tache creee"
        COLUMN_CHANGED = "column_changed", "Deplacee dans une colonne"
        TASK_COMPLETED = "task_completed", "Tache terminee (100%)"

    class Action(models.TextChoices):
        MOVE_TO_COLUMN = "move_to_column", "Deplacer vers une colonne"
        SET_PRIORITY = "set_priority", "Changer la priorite"
        ADD_LABEL = "add_label", "Ajouter une etiquette"
        NOTIFY_ASSIGNEES = "notify_assignees", "Notifier les assignes"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="automation_rules")
    name = models.CharField(max_length=120)
    trigger = models.CharField(max_length=20, choices=Trigger.choices)
    # Only meaningful (and required) when trigger == COLUMN_CHANGED.
    trigger_column = models.ForeignKey(
        BoardColumn, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    action_column = models.ForeignKey(
        BoardColumn, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    action_priority = models.CharField(max_length=10, blank=True)
    action_label = models.ForeignKey(Label, on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.project.name} / {self.name}"


DEFAULT_COLUMNS = [
    {"name": "A faire", "color": "#90A4AE", "order": 0, "is_done_column": False},
    {"name": "En cours", "color": "#42A5F5", "order": 1, "is_done_column": False},
    {"name": "En revue", "color": "#FFA726", "order": 2, "is_done_column": False},
    {"name": "Termine", "color": "#66BB6A", "order": 3, "is_done_column": True},
]
