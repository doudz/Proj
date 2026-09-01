from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.notifications.models import Notification


def push_notification(user_id, verb, task, actor=None):
    """Create a Notification row and push it over the user's websocket group,
    if any consumer is currently listening."""
    notification = Notification.objects.create(recipient_id=user_id, verb=verb, task=task, actor=actor)
    layer = get_channel_layer()
    if layer:
        async_to_sync(layer.group_send)(
            f"user_{user_id}",
            {
                "type": "notification.message",
                "payload": {
                    "id": notification.id,
                    "verb": notification.verb,
                    "task_id": task.id,
                    "task_title": task.title,
                    "created_at": notification.created_at.isoformat(),
                },
            },
        )
    return notification
