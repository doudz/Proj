from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.projects.models import BoardColumn, Label, Project

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


class ProjectSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        source="members", queryset=User.objects.all(), many=True, write_only=True, required=False
    )
    columns = BoardColumnSerializer(many=True, read_only=True)
    labels = LabelSerializer(many=True, read_only=True)
    tasks_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

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
            "created_at",
            "members",
            "member_ids",
            "columns",
            "labels",
            "tasks_count",
            "progress",
        ]
        read_only_fields = ["id", "created_at"]

    def get_tasks_count(self, obj):
        return obj.tasks.count()

    def get_progress(self, obj):
        total = obj.tasks.count()
        if not total:
            return 0
        done = obj.tasks.filter(progress=100).count()
        return round(done / total * 100)
