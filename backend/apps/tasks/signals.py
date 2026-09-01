from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.tasks.models import Task


@receiver(m2m_changed, sender=Task.assignees.through)
def notify_on_assignment(sender, instance, action, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    layer = get_channel_layer()
    for user_id in pk_set:
        if instance.created_by_id == user_id:
            continue
        notification = Notification.objects.create(
            recipient_id=user_id,
            verb=f"vous a assigne la tache « {instance.title} »",
            task=instance,
            actor=instance.created_by,
        )
        if layer:
            async_to_sync(layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "notification.message",
                    "payload": {
                        "id": notification.id,
                        "verb": notification.verb,
                        "task_id": instance.id,
                        "task_title": instance.title,
                        "created_at": notification.created_at.isoformat(),
                    },
                },
            )
