"""Execution engine for apps.projects.models.AutomationRule.

Rules are looked up and applied synchronously, right where the triggering
change happens (see apps.tasks.views). Actions can themselves trigger other
rules (moving a task to a column a rule reacts to, for instance) - that
chaining is intentional, but capped so a badly configured pair of rules
cannot loop forever.
"""

from apps.notifications.services import push_notification

MAX_CHAIN_DEPTH = 10


def run_rules(task, trigger, *, depth=0):
    if depth > MAX_CHAIN_DEPTH:
        return
    from apps.projects.models import AutomationRule

    rules = AutomationRule.objects.filter(project_id=task.project_id, trigger=trigger, enabled=True)
    if trigger == AutomationRule.Trigger.COLUMN_CHANGED:
        rules = rules.filter(trigger_column_id=task.column_id)
    for rule in rules.select_related("action_column", "action_label"):
        _apply(task, rule, depth)


def _apply(task, rule, depth):
    from apps.projects.models import AutomationRule

    Action = AutomationRule.Action

    if rule.action == Action.MOVE_TO_COLUMN and rule.action_column_id and task.column_id != rule.action_column_id:
        task.column_id = rule.action_column_id
        task.save(update_fields=["column"])
        run_rules(task, AutomationRule.Trigger.COLUMN_CHANGED, depth=depth + 1)

    elif rule.action == Action.SET_PRIORITY and rule.action_priority and task.priority != rule.action_priority:
        task.priority = rule.action_priority
        task.save(update_fields=["priority"])

    elif rule.action == Action.ADD_LABEL and rule.action_label_id:
        task.labels.add(rule.action_label_id)

    elif rule.action == Action.NOTIFY_ASSIGNEES:
        for user_id in task.assignees.values_list("id", flat=True):
            push_notification(user_id, f"regle automatique « {rule.name} » declenchee", task)
