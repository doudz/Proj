import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.tasks.models import Task

logger = logging.getLogger(__name__)


def _push_notification(user_id, verb, task, actor=None):
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


@receiver(m2m_changed, sender=Task.assignees.through)
def notify_on_assignment(sender, instance, action, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    for user_id in pk_set:
        if instance.created_by_id == user_id:
            continue
        _push_notification(user_id, f"vous a assigne la tache « {instance.title} »", instance, actor=instance.created_by)


@receiver(pre_save, sender=Task)
def _stash_previous_progress(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_progress = (
            Task.objects.filter(pk=instance.pk).values_list("progress", flat=True).first()
        )
    else:
        instance._previous_progress = None


@receiver(post_save, sender=Task)
def notify_dependents_when_unblocked(sender, instance, created, **kwargs):
    """When a task reaches 100%, check every task strictly depending on it: if it is
    now unblocked and still in its initial "a commencer" state, notify its assignees
    (in-app + realtime + e-mail) that the task is ready to start."""
    previous = getattr(instance, "_previous_progress", None)
    if created or previous is None or previous >= 100 or instance.progress < 100:
        return

    dependent_links = instance.successor_links.filter(enforce_blocking=True).select_related("successor")
    for link in dependent_links:
        successor = link.successor
        if successor.is_ready_to_start():
            notify_task_available(successor)


def notify_task_available(task):
    for user in task.assignees.all():
        _push_notification(user.id, f"la tache « {task.title} » est disponible (dependance terminee)", task)
        send_task_available_email(user, task)


def send_task_available_email(user, task):
    if not user.email:
        return
    subject = f"[GanttFlow] Tache disponible : {task.title}"
    link = f"{settings.FRONTEND_URL.rstrip('/')}/projects/{task.project_id}"
    message = (
        f"Bonjour {user.first_name or user.email},\n\n"
        f"La tache dont dependait « {task.title} » vient d'etre terminee : "
        f"cette tache peut maintenant demarrer.\n\n"
        f"Voir le projet : {link}\n"
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception:
        logger.warning("Echec de l'envoi de l'e-mail de disponibilite pour la tache %s", task.id, exc_info=True)
