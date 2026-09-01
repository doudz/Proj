from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True, default="")

    class Meta:
        model = Notification
        fields = ["id", "actor", "verb", "task", "task_title", "is_read", "created_at"]
        read_only_fields = fields
