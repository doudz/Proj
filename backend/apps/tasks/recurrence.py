"""Spawns the next occurrence of a recurring task once it is completed.

A recurring task is a normal task with `recurrence` set; there is no
separate "series" object. Completing one occurrence creates the next with
its dates shifted by the recurrence period and its progress reset - the
new task carries the same recurrence setting, so the chain continues on its
own for as long as someone keeps completing occurrences.
"""

import calendar
from datetime import timedelta


def _add_period(value, recurrence):
    from apps.tasks.models import Task

    if recurrence == Task.Recurrence.DAILY:
        return value + timedelta(days=1)
    if recurrence == Task.Recurrence.WEEKLY:
        return value + timedelta(days=7)
    if recurrence == Task.Recurrence.MONTHLY:
        month = value.month + 1
        year = value.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)
    return value


def spawn_next_occurrence(task):
    """Create and return the next occurrence of `task`, or None if it isn't recurring."""
    from apps.tasks.models import CustomFieldValue, Task

    if task.recurrence == Task.Recurrence.NONE:
        return None

    first_column = task.project.columns.order_by("order").first()
    clone = Task.objects.create(
        project=task.project,
        column=first_column,
        parent=task.parent,
        title=task.title,
        description=task.description,
        start_date=_add_period(task.start_date, task.recurrence) if task.start_date else None,
        due_date=_add_period(task.due_date, task.recurrence) if task.due_date else None,
        is_milestone=task.is_milestone,
        priority=task.priority,
        color=task.color,
        order=task.order,
        recurrence=task.recurrence,
        created_by=task.created_by,
    )
    clone.assignees.set(task.assignees.all())
    clone.external_assignees.set(task.external_assignees.all())
    clone.labels.set(task.labels.all())
    values = [
        CustomFieldValue(field_id=value.field_id, task=clone, value=value.value)
        for value in task.custom_values.all()
    ]
    if values:
        CustomFieldValue.objects.bulk_create(values)
    return clone
