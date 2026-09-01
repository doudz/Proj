import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from apps.notifications.services import push_notification as _push_notification
from apps.tasks.models import Task

logger = logging.getLogger(__name__)


def _send_email(to_email, to_name, subject, body):
    if not to_email:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)
    except Exception:
        logger.warning("Echec de l'envoi d'un e-mail a %s", to_email, exc_info=True)


@receiver(m2m_changed, sender=Task.assignees.through)
def notify_on_assignment(sender, instance, action, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    for user_id in pk_set:
        if instance.created_by_id == user_id:
            continue
        _push_notification(user_id, f"vous a assigne la tache « {instance.title} »", instance, actor=instance.created_by)


@receiver(m2m_changed, sender=Task.external_assignees.through)
def notify_on_external_assignment(sender, instance, action, pk_set, **kwargs):
    """External contacts have no account and can't see in-app notifications, so an
    e-mail is the only way to let them know they were assigned a task."""
    if action != "post_add" or not pk_set:
        return
    for contact in instance.external_assignees.filter(pk__in=pk_set):
        link = f"{settings.FRONTEND_URL.rstrip('/')}/projects/{instance.project_id}"
        body = (
            f"Bonjour {contact.name},\n\n"
            f"Une tache vous a ete assignee dans le projet « {instance.project.name} » : « {instance.title} ».\n\n"
        )
        if instance.description:
            body += f"Description :\n{instance.description}\n\n"
        if instance.start_date or instance.due_date:
            body += f"Periode prevue : {instance.start_date or '?'} -> {instance.due_date or '?'}\n\n"
        body += (
            "Cette tache est geree dans GanttFlow. Vous n'avez pas de compte sur l'outil : "
            "contactez la personne qui vous l'a assignee pour toute question ou mise a jour.\n"
            f"(Reference interne : {link})\n"
        )
        _send_email(contact.email, contact.name, f"[GanttFlow] Nouvelle tache assignee : {instance.title}", body)


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
    (in-app + realtime + e-mail for members, e-mail only for external contacts)."""
    previous = getattr(instance, "_previous_progress", None)
    if created or previous is None or previous >= 100 or instance.progress < 100:
        return

    dependent_links = instance.successor_links.filter(enforce_blocking=True).select_related("successor")
    for link in dependent_links:
        successor = link.successor
        if successor.is_ready_to_start():
            notify_task_available(successor)


def notify_task_available(task):
    link = f"{settings.FRONTEND_URL.rstrip('/')}/projects/{task.project_id}"
    for user in task.assignees.all():
        _push_notification(user.id, f"la tache « {task.title} » est disponible (dependance terminee)", task)
        body = (
            f"Bonjour {user.first_name or user.email},\n\n"
            f"La tache dont dependait « {task.title} » vient d'etre terminee : "
            f"cette tache peut maintenant demarrer.\n\n"
            f"Voir le projet : {link}\n"
        )
        _send_email(user.email, user.first_name, f"[GanttFlow] Tache disponible : {task.title}", body)

    for contact in task.external_assignees.all():
        body = (
            f"Bonjour {contact.name},\n\n"
            f"La tache dont dependait « {task.title} » (projet « {task.project.name} ») vient d'etre terminee : "
            f"cette tache peut maintenant demarrer.\n\n"
            "Vous n'avez pas de compte sur GanttFlow : contactez la personne qui vous a assigne cette tache "
            "pour toute question ou mise a jour.\n"
            f"(Reference interne : {link})\n"
        )
        _send_email(contact.email, contact.name, f"[GanttFlow] Tache disponible : {task.title}", body)
