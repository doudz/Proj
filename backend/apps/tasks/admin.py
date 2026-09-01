from django.contrib import admin

from apps.tasks.models import ActivityLog, Attachment, Comment, CustomFieldValue, Task, TaskDependency


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


admin.site.register(Attachment)
admin.site.register(ActivityLog)
