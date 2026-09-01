from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.projects.models import BoardColumn, Label, Project, ProjectMembership
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
    tasks_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

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
            "created_at",
            "members",
            "columns",
            "labels",
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
