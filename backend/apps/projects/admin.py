from django.contrib import admin

from apps.projects.models import BoardColumn, CustomField, Label, Project


class BoardColumnInline(admin.TabularInline):
    model = BoardColumn
    extra = 0


class CustomFieldInline(admin.TabularInline):
    model = CustomField
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "status", "is_template", "start_date", "end_date"]
    list_filter = ["status", "is_template", "workspace"]
    search_fields = ["name"]
    inlines = [BoardColumnInline, CustomFieldInline]


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "field_type", "order", "show_in_list"]
    list_filter = ["field_type", "project"]


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "color"]
