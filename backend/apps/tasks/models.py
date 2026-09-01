from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.projects.models import BoardColumn, Label, Project


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Basse"
        MEDIUM = "medium", "Moyenne"
        HIGH = "high", "Haute"
        URGENT = "urgent", "Urgente"

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

    assignees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="assigned_tasks", blank=True)
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
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/")
    filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name
        super().save(*args, **kwargs)


class ActivityLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="activity")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    verb = models.CharField(max_length=255)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
