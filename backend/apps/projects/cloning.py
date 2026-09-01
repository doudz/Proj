from django.db import transaction

from apps.projects.models import BoardColumn, CustomField, Label, Project, ProjectMembership


def _earliest_planned_date(tasks):
    """The first planned date of a task set, used as the anchor when re-dating a clone forward from a start date."""
    dates = [d for task in tasks for d in (task.start_date, task.due_date) if d]
    return min(dates) if dates else None


def _latest_planned_date(tasks):
    """The last planned date of a task set, used as the anchor when re-dating a clone backward from an end date."""
    dates = [d for task in tasks for d in (task.start_date, task.due_date) if d]
    return max(dates) if dates else None


def _shifted(value, delta_days):
    if value is None:
        return None
    if not delta_days:
        return value
    return value + delta_days


@transaction.atomic
def clone_project(
    source, *, name, created_by, is_template=False, start_date=None, end_date=None, keep_assignees=True
):
    """Deep-copy a project into a new one.

    Copies the structure (columns, labels, custom fields) and the work
    breakdown (tasks, their hierarchy, labels, custom values and
    dependencies). Progress and history - baseline dates, actual dates,
    progress, comments, attachments, activity - are deliberately not copied:
    a clone always starts as a fresh plan.

    Every planned date is shifted by the same number of days, so the whole
    plan - including which task drives which via a dependency - keeps its
    relative shape. The shift can be anchored from either end (pass at most
    one): `start_date` lines up the earliest task's start on that day and
    lets the plan run forward; `end_date` lines up the latest task's end on
    that day and lets the plan run backward from a deadline.
    """
    from apps.tasks.models import CustomFieldValue, Task, TaskDependency

    source_tasks = list(source.tasks.all().prefetch_related("labels", "assignees", "external_assignees", "custom_values"))

    delta_days = None
    if start_date:
        anchor = _earliest_planned_date(source_tasks) or source.start_date
        if anchor:
            delta_days = start_date - anchor
    elif end_date:
        anchor = _latest_planned_date(source_tasks) or source.end_date
        if anchor:
            delta_days = end_date - anchor

    project = Project.objects.create(
        workspace=source.workspace,
        name=name,
        description=source.description,
        color=source.color,
        icon=source.icon,
        status=Project.Status.ACTIVE,
        start_date=_shifted(source.start_date, delta_days) or start_date,
        end_date=_shifted(source.end_date, delta_days) or end_date,
        is_template=is_template,
        created_by=created_by,
    )
    ProjectMembership.objects.create(project=project, user=created_by, role=ProjectMembership.Role.ADMIN)

    column_map = {}
    for column in source.columns.all():
        clone = BoardColumn.objects.create(
            project=project,
            name=column.name,
            color=column.color,
            order=column.order,
            is_done_column=column.is_done_column,
        )
        column_map[column.id] = clone

    label_map = {}
    for label in source.labels.all():
        label_map[label.id] = Label.objects.create(project=project, name=label.name, color=label.color)

    field_map = {}
    for field in source.custom_fields.all():
        field_map[field.id] = CustomField.objects.create(
            project=project,
            name=field.name,
            field_type=field.field_type,
            options=field.options,
            order=field.order,
            show_in_list=field.show_in_list,
        )

    task_map = {}
    for task in source_tasks:
        clone = Task.objects.create(
            project=project,
            column=column_map.get(task.column_id),
            title=task.title,
            description=task.description,
            start_date=_shifted(task.start_date, delta_days),
            due_date=_shifted(task.due_date, delta_days),
            is_milestone=task.is_milestone,
            priority=task.priority,
            color=task.color,
            order=task.order,
            created_by=created_by,
        )
        task_map[task.id] = clone

    # Second pass: the hierarchy can only be wired once every clone exists.
    for task in source_tasks:
        if task.parent_id and task.parent_id in task_map:
            clone = task_map[task.id]
            clone.parent = task_map[task.parent_id]
            clone.save(update_fields=["parent"])

    for task in source_tasks:
        clone = task_map[task.id]
        labels = [label_map[label.id] for label in task.labels.all() if label.id in label_map]
        if labels:
            clone.labels.set(labels)
        if keep_assignees:
            clone.assignees.set(task.assignees.all())
            clone.external_assignees.set(task.external_assignees.all())
        values = [
            CustomFieldValue(field=field_map[value.field_id], task=clone, value=value.value)
            for value in task.custom_values.all()
            if value.field_id in field_map
        ]
        if values:
            CustomFieldValue.objects.bulk_create(values)

    dependencies = TaskDependency.objects.filter(predecessor__project=source, successor__project=source)
    TaskDependency.objects.bulk_create(
        [
            TaskDependency(
                predecessor=task_map[dep.predecessor_id],
                successor=task_map[dep.successor_id],
                type=dep.type,
                lag_days=dep.lag_days,
                enforce_blocking=dep.enforce_blocking,
            )
            for dep in dependencies
            if dep.predecessor_id in task_map and dep.successor_id in task_map
        ]
    )

    return project
