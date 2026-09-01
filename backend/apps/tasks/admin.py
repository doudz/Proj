from django.contrib import admin

from apps.tasks.models import (
    ActivityLog,
    Attachment,
    AttachmentComment,
    Comment,
    CustomFieldValue,
    Task,
    TaskDependency,
    TimeEntry,
)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "column", "start_date", "due_date", "progress", "priority"]
    list_filter = ["priority", "project"]
    search_fields = ["title"]


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ["predecessor", "successor", "type", "lag_days"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["task", "author", "created_at"]


@admin.register(CustomFieldValue)
class CustomFieldValueAdmin(admin.ModelAdmin):
    list_display = ["task", "field", "value"]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ["task", "user", "started_at", "ended_at", "duration_minutes"]
    list_filter = ["user"]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["filename", "task", "status", "uploaded_by", "uploaded_at"]
    list_filter = ["status"]


admin.site.register(AttachmentComment)
admin.site.register(ActivityLog)
