from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.projects.models import Label
from apps.projects.serializers import LabelSerializer
from apps.tasks.models import ActivityLog, Attachment, Comment, Task, TaskDependency

User = get_user_model()


class TaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDependency
        fields = ["id", "predecessor", "successor", "type", "lag_days"]
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
    labels = LabelSerializer(many=True, read_only=True)
    label_ids = serializers.PrimaryKeyRelatedField(
        source="labels", queryset=Label.objects.all(), many=True, write_only=True, required=False
    )
    predecessors = TaskDependencySerializer(source="predecessor_links", many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    subtasks_count = serializers.SerializerMethodField()
    start_variance_days = serializers.SerializerMethodField()
    end_variance_days = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "column",
            "parent",
            "title",
            "description",
            "start_date",
            "due_date",
            "baseline_start_date",
            "baseline_end_date",
            "actual_start_date",
            "actual_end_date",
            "start_variance_days",
            "end_variance_days",
            "is_milestone",
            "progress",
            "priority",
            "color",
            "order",
            "assignees",
            "assignee_ids",
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

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
