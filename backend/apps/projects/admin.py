from django.contrib import admin

from apps.projects.models import BoardColumn, Label, Project


class BoardColumnInline(admin.TabularInline):
    model = BoardColumn
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "status", "start_date", "end_date"]
    list_filter = ["status", "workspace"]
    search_fields = ["name"]
    inlines = [BoardColumnInline]


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "color"]
