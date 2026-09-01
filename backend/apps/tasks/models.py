from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.projects.models import BoardColumn, CustomField, Label, Project


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Basse"
        MEDIUM = "medium", "Moyenne"
        HIGH = "high", "Haute"
        URGENT = "urgent", "Urgente"

    class Recurrence(models.TextChoices):
        NONE = "none", "Aucune"
        DAILY = "daily", "Quotidienne"
        WEEKLY = "weekly", "Hebdomadaire"
        MONTHLY = "monthly", "Mensuelle"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    column = models.ForeignKey(BoardColumn, on_delete=models.SET_NULL, null=True, related_name="tasks")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="subtasks")

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_milestone = models.BooleanField(default=False)

    # Reference plan, captured on demand from start_date/due_date (Project.set-baseline).
    # Frozen until the baseline is recaptured or cleared - used to measure schedule drift.
    baseline_start_date = models.DateField(null=True, blank=True)
    baseline_end_date = models.DateField(null=True, blank=True)

    # What actually happened - deliberately unconstrained relative to start_date/due_date
    # so a task can be started or finished earlier or later than planned.
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)

    progress = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    color = models.CharField(max_length=7, blank=True)
    order = models.PositiveIntegerField(default=0)
    # When set, completing this task (progress reaching 100) spawns the next
    # occurrence instead of just staying done - see apps.tasks.recurrence.
    recurrence = models.CharField(max_length=10, choices=Recurrence.choices, default=Recurrence.NONE)

    assignees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="assigned_tasks", blank=True)
    # External people/subcontractors without a GanttFlow account (outsourced work).
    # Notified by e-mail only - see apps.tasks.signals.
    external_assignees = models.ManyToManyField(
        "workspaces.ExternalContact", related_name="assigned_tasks", blank=True
    )
    labels = models.ManyToManyField(Label, related_name="tasks", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="tasks_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["project", "start_date"]),
            models.Index(fields=["project", "due_date"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_done(self):
        return self.progress >= 100

    @property
    def duration_days(self):
        """Planned length in calendar days, both ends included (1 day = same-day task)."""
        if self.start_date and self.due_date:
            return (self.due_date - self.start_date).days + 1
        return None

    def is_blocked(self):
        """True if at least one *enforced* dependency links to a predecessor that isn't done yet."""
        return self.predecessor_links.filter(enforce_blocking=True).exclude(predecessor__progress=100).exists()

    def blocking_predecessor_tasks(self):
        return [
            link.predecessor
            for link in self.predecessor_links.filter(enforce_blocking=True)
            .exclude(predecessor__progress=100)
            .select_related("predecessor")
        ]

    def is_ready_to_start(self):
        """A task is 'available' once nothing blocks it and it hasn't been started yet."""
        return self.progress == 0 and self.actual_start_date is None and not self.is_blocked()


class CustomFieldValue(models.Model):
    """The value a given task holds for one of its project's custom fields.

    Always stored as text; apps.projects.models.CustomField.field_type says how
    to read it back (an empty string means "not filled in").
    """

    field = models.ForeignKey(CustomField, on_delete=models.CASCADE, related_name="values")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="custom_values")
    value = models.TextField(blank=True)

    class Meta:
        unique_together = ("field", "task")

    def __str__(self):
        return f"{self.task.title} / {self.field.name} = {self.value}"


class TaskDependency(models.Model):
    class Type(models.TextChoices):
        FINISH_TO_START = "FS", "Fin -> Debut"
        START_TO_START = "SS", "Debut -> Debut"
        FINISH_TO_FINISH = "FF", "Fin -> Fin"
        START_TO_FINISH = "SF", "Debut -> Fin"

    predecessor = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="successor_links")
    successor = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="predecessor_links")
    type = models.CharField(max_length=2, choices=Type.choices, default=Type.FINISH_TO_START)
    lag_days = models.IntegerField(default=0)
    # Optional strict mode: while true, the successor cannot be started (see Task.is_blocked)
    # until this predecessor reaches 100% progress.
    enforce_blocking = models.BooleanField(default=False)

    class Meta:
        unique_together = ("predecessor", "successor")
        verbose_name_plural = "task dependencies"

    def __str__(self):
        return f"{self.predecessor} -> {self.successor} ({self.type})"


class Comment(models.Model):
    """Discussion / chat thread attached to a task."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} on {self.task}: {self.body[:30]}"


class Attachment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuve"
        CHANGES_REQUESTED = "changes_requested", "A revoir"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/")
    filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # Lightweight proofing workflow: an admin marks a file approved or sends it
    # back for changes. Optional - most attachments simply stay "pending" and
    # that is fine, it just means nobody has reviewed it yet.
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name
        super().save(*args, **kwargs)

    @property
    def is_image(self):
        return self.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"))


class AttachmentComment(models.Model):
    """A remark on an attachment - optionally pinned to a point on an image
    (x_percent/y_percent, both 0-100) for in-context proofing feedback."""

    attachment = models.ForeignKey(Attachment, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = models.TextField()
    x_percent = models.FloatField(null=True, blank=True)
    y_percent = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} on {self.attachment}: {self.body[:30]}"


class TimeEntry(models.Model):
    """A stretch of time someone spent on a task - either a running/stopped
    timer (started_at set, ended_at filled in on stop) or a manually logged
    stretch (both given up front)."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="time_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="time_entries")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user} on {self.task} ({self.duration_minutes} min)"

    @property
    def duration_minutes(self):
        end = self.ended_at or timezone.now()
        return max(0, int((end - self.started_at).total_seconds() // 60))

    @property
    def is_running(self):
        return self.ended_at is None


class ActivityLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="activity")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    verb = models.CharField(max_length=255)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
