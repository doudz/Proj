from datetime import timedelta

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.projects.models import Label
from apps.projects.permissions import can_edit_task_state, is_project_admin
from apps.projects.serializers import LabelSerializer
from apps.tasks.models import ActivityLog, Attachment, Comment, CustomFieldValue, Task, TaskDependency
from apps.workspaces.models import ExternalContact
from apps.workspaces.serializers import ExternalContactSerializer

User = get_user_model()


class TaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDependency
        fields = ["id", "predecessor", "successor", "type", "lag_days", "enforce_blocking"]
        read_only_fields = ["id"]


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "task", "author", "body", "created_at", "edited_at"]
        read_only_fields = ["id", "author", "created_at", "edited_at"]


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = Attachment
        fields = ["id", "task", "file", "filename", "uploaded_by", "uploaded_at"]
        read_only_fields = ["id", "uploaded_by", "uploaded_at", "filename"]


class ActivityLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = ["id", "task", "user", "verb", "meta", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    assignees = UserSerializer(many=True, read_only=True)
    assignee_ids = serializers.PrimaryKeyRelatedField(
        source="assignees", queryset=User.objects.all(), many=True, write_only=True, required=False
    )
    external_assignees = ExternalContactSerializer(many=True, read_only=True)
    external_assignee_ids = serializers.PrimaryKeyRelatedField(
        source="external_assignees", queryset=ExternalContact.objects.all(), many=True, write_only=True, required=False
    )
    labels = LabelSerializer(many=True, read_only=True)
    label_ids = serializers.PrimaryKeyRelatedField(
        source="labels", queryset=Label.objects.all(), many=True, write_only=True, required=False
    )
    predecessors = TaskDependencySerializer(source="predecessor_links", many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    subtasks_count = serializers.SerializerMethodField()
    start_variance_days = serializers.SerializerMethodField()
    end_variance_days = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    blocking_predecessor_titles = serializers.SerializerMethodField()
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_color = serializers.CharField(source="project.color", read_only=True)
    project_icon = serializers.CharField(source="project.icon", read_only=True)
    workspace_id = serializers.IntegerField(source="project.workspace_id", read_only=True)
    workspace_name = serializers.CharField(source="project.workspace.name", read_only=True)
    can_edit_full = serializers.SerializerMethodField()
    can_edit_state = serializers.SerializerMethodField()
    # Planned length in days: writing it moves due_date (or start_date when only
    # the due date is known), so a task can be scheduled by duration instead of
    # by picking an end date by hand.
    duration_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    custom_values = serializers.SerializerMethodField()
    custom_field_values = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "project_name",
            "project_color",
            "project_icon",
            "workspace_id",
            "workspace_name",
            "column",
            "parent",
            "title",
            "description",
            "start_date",
            "due_date",
            "duration_days",
            "custom_values",
            "custom_field_values",
            "baseline_start_date",
            "baseline_end_date",
            "actual_start_date",
            "actual_end_date",
            "start_variance_days",
            "end_variance_days",
            "is_blocked",
            "blocking_predecessor_titles",
            "can_edit_full",
            "can_edit_state",
            "is_milestone",
            "progress",
            "priority",
            "color",
            "order",
            "assignees",
            "assignee_ids",
            "external_assignees",
            "external_assignee_ids",
            "labels",
            "label_ids",
            "predecessors",
            "comments_count",
            "subtasks_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "baseline_start_date",
            "baseline_end_date",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_subtasks_count(self, obj):
        return obj.subtasks.count()

    def get_start_variance_days(self, obj):
        if obj.baseline_start_date and obj.actual_start_date:
            return (obj.actual_start_date - obj.baseline_start_date).days
        return None

    def get_end_variance_days(self, obj):
        if obj.baseline_end_date and obj.actual_end_date:
            return (obj.actual_end_date - obj.baseline_end_date).days
        return None

    def get_is_blocked(self, obj):
        return obj.is_blocked()

    def get_blocking_predecessor_titles(self, obj):
        return [t.title for t in obj.blocking_predecessor_tasks()]

    def get_can_edit_full(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return is_project_admin(request.user, obj.project)

    def get_can_edit_state(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return can_edit_task_state(request.user, obj)

    def get_custom_values(self, obj):
        """{"<custom_field_id>": "value"} - the field definitions themselves come
        with the project, so the task only carries what it holds."""
        return {str(value.field_id): value.value for value in obj.custom_values.all()}

    def _apply_duration(self, validated_data, instance=None):
        """Turn a requested duration into concrete dates.

        start_date + duration wins over an explicitly sent due_date, since
        asking for a duration is asking for the end to be recomputed.
        """
        duration = validated_data.pop("duration_days", None)
        if duration is None:
            return validated_data
        start = validated_data.get("start_date", getattr(instance, "start_date", None))
        due = validated_data.get("due_date", getattr(instance, "due_date", None))
        if start:
            validated_data["due_date"] = start + timedelta(days=duration - 1)
        elif due:
            validated_data["start_date"] = due - timedelta(days=duration - 1)
        return validated_data

    def _save_custom_values(self, task, raw_values):
        if not raw_values:
            return
        allowed_ids = set(task.project.custom_fields.values_list("id", flat=True))
        for key, value in raw_values.items():
            try:
                field_id = int(key)
            except (TypeError, ValueError):
                continue
            if field_id not in allowed_ids:
                continue
            CustomFieldValue.objects.update_or_create(
                field_id=field_id, task=task, defaults={"value": "" if value is None else str(value)}
            )

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        custom_values = validated_data.pop("custom_field_values", None)
        validated_data = self._apply_duration(validated_data)
        task = super().create(validated_data)
        self._save_custom_values(task, custom_values)
        return task

    def update(self, instance, validated_data):
        custom_values = validated_data.pop("custom_field_values", None)
        validated_data = self._apply_duration(validated_data, instance)
        task = super().update(instance, validated_data)
        self._save_custom_values(task, custom_values)
        return task
