from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.projects.models import (
    AutomationRule,
    BoardColumn,
    CustomField,
    Label,
    Project,
    ProjectCustomFieldValue,
    ProjectMembership,
)
from apps.projects.permissions import get_project_role

User = get_user_model()


class BoardColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardColumn
        fields = ["id", "project", "name", "color", "order", "is_done_column"]
        read_only_fields = ["id"]


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ["id", "project", "name", "color"]
        read_only_fields = ["id"]


class CustomFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomField
        fields = ["id", "project", "name", "field_type", "level", "options", "order", "show_in_list"]
        read_only_fields = ["id"]


class AutomationRuleSerializer(serializers.ModelSerializer):
    # Declared explicitly (rather than left to ModelSerializer's default,
    # non-nullable mapping) so a client can send null here, symmetric with how
    # it sends null for the two FK-backed action_* fields when they don't
    # apply to the chosen action.
    action_priority = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = AutomationRule
        fields = [
            "id",
            "project",
            "name",
            "trigger",
            "trigger_column",
            "action",
            "action_column",
            "action_priority",
            "action_label",
            "enabled",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        # action_priority is a plain (non-nullable) CharField - a client that
        # sends null for "not applicable to this action" (the natural thing to
        # do, symmetric with the two FK fields) would otherwise hit a raw
        # "may not be null" error instead of the friendlier checks below.
        if attrs.get("action_priority") is None and "action_priority" in attrs:
            attrs["action_priority"] = ""

        trigger = attrs.get("trigger", getattr(self.instance, "trigger", None))
        if trigger == AutomationRule.Trigger.COLUMN_CHANGED and not attrs.get(
            "trigger_column", getattr(self.instance, "trigger_column", None)
        ):
            raise serializers.ValidationError(
                {"trigger_column": "Indiquez la colonne qui declenche cette regle."}
            )
        action = attrs.get("action", getattr(self.instance, "action", None))
        required_by_action = {
            AutomationRule.Action.MOVE_TO_COLUMN: "action_column",
            AutomationRule.Action.SET_PRIORITY: "action_priority",
            AutomationRule.Action.ADD_LABEL: "action_label",
        }
        field = required_by_action.get(action)
        if field and not attrs.get(field, getattr(self.instance, field, None)):
            raise serializers.ValidationError({field: "Ce champ est requis pour cette action."})
        return attrs


class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ["id", "project", "user", "role", "added_at"]
        read_only_fields = ["id", "project", "added_at"]


class ProjectSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    columns = BoardColumnSerializer(many=True, read_only=True)
    labels = LabelSerializer(many=True, read_only=True)
    custom_fields = CustomFieldSerializer(many=True, read_only=True)
    tasks_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    # Values for this project's own (level="project") custom fields, shown in
    # the project header - the project-level counterpart to how a task holds
    # custom_values/custom_field_values for level="task" fields.
    custom_values = serializers.SerializerMethodField()
    custom_field_values = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = Project
        fields = [
            "id",
            "workspace",
            "name",
            "description",
            "color",
            "icon",
            "status",
            "start_date",
            "end_date",
            "baseline_captured_at",
            "is_template",
            "created_at",
            "members",
            "columns",
            "labels",
            "custom_fields",
            "custom_values",
            "custom_field_values",
            "tasks_count",
            "progress",
            "my_role",
        ]
        read_only_fields = ["id", "created_at", "baseline_captured_at"]

    def get_tasks_count(self, obj):
        return obj.tasks.count()

    def get_progress(self, obj):
        total = obj.tasks.count()
        if not total:
            return 0
        done = obj.tasks.filter(progress=100).count()
        return round(done / total * 100)

    def get_my_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return get_project_role(request.user, obj)

    def get_custom_values(self, obj):
        """{"<custom_field_id>": "value"} for this project's level="project" fields."""
        return {str(value.field_id): value.value for value in obj.custom_values.all()}

    def _save_custom_values(self, project, raw_values):
        if not raw_values:
            return
        allowed_ids = set(
            project.custom_fields.filter(level=CustomField.Level.PROJECT).values_list("id", flat=True)
        )
        for key, value in raw_values.items():
            try:
                field_id = int(key)
            except (TypeError, ValueError):
                continue
            if field_id not in allowed_ids:
                continue
            ProjectCustomFieldValue.objects.update_or_create(
                field_id=field_id, project=project, defaults={"value": "" if value is None else str(value)}
            )

    def create(self, validated_data):
        custom_values = validated_data.pop("custom_field_values", None)
        project = super().create(validated_data)
        self._save_custom_values(project, custom_values)
        return project

    def update(self, instance, validated_data):
        custom_values = validated_data.pop("custom_field_values", None)
        project = super().update(instance, validated_data)
        self._save_custom_values(project, custom_values)
        return project
