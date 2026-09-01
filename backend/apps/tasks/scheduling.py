"""Dependency-driven scheduling.

Once a task has a predecessor, its start date is no longer something a human
picks: it falls out of the link. A finish-to-start link means the successor
begins the day after its predecessor ends, and the other link types constrain
the pair in their own way. When several predecessors apply, the latest of the
constraints wins - the task can only begin once every link allows it.

Because of that, moving a task automatically drags everything downstream with
it, each successor keeping the duration it had.
"""

from datetime import timedelta

MAX_CASCADE_DEPTH = 200


def _duration_of(task):
    if task.start_date and task.due_date:
        return (task.due_date - task.start_date).days + 1
    return None


def _constrained_start(link, predecessor, successor):
    """The earliest start `successor` may take to satisfy this single link.

    Returns None when the predecessor is not scheduled enough for the link to
    say anything (for example a finish-to-start link whose predecessor has no
    end date yet).
    """
    lag = timedelta(days=link.lag_days)

    if link.type == "FS":
        if not predecessor.due_date:
            return None
        return predecessor.due_date + timedelta(days=1) + lag

    if link.type == "SS":
        if not predecessor.start_date:
            return None
        return predecessor.start_date + lag

    # FF and SF constrain the *end* of the successor, so they only translate
    # into a start date once we know how long the successor lasts.
    duration = _duration_of(successor)
    if duration is None:
        return None

    if link.type == "FF":
        if not predecessor.due_date:
            return None
        return predecessor.due_date + lag - timedelta(days=duration - 1)

    if link.type == "SF":
        if not predecessor.start_date:
            return None
        return predecessor.start_date + lag - timedelta(days=duration - 1)

    return None


def computed_start_date(task):
    """The start date the dependencies impose on `task`, or None if it is free."""
    links = task.predecessor_links.select_related("predecessor")
    candidates = [
        start
        for link in links
        if (start := _constrained_start(link, link.predecessor, task)) is not None
    ]
    return max(candidates) if candidates else None


def is_dependency_scheduled(task):
    """True when at least one predecessor drives this task's start date."""
    return task.predecessor_links.exists()


def apply_schedule(task, *, save=True):
    """Snap a task onto the start date its dependencies impose.

    The duration is preserved: shifting the start moves the end by the same
    amount. A task with no scheduled predecessor, or one without dates yet, is
    left untouched. Returns True when something actually moved.
    """
    start = computed_start_date(task)
    if start is None or start == task.start_date:
        return False

    duration = _duration_of(task)
    task.start_date = start
    if duration is not None:
        task.due_date = start + timedelta(days=duration - 1)
    elif task.due_date and task.due_date < start:
        # No known duration but the old end is now in the past of the new
        # start - collapse it to a single day rather than leaving it invalid.
        task.due_date = start
    if save:
        fields = ["start_date", "due_date"] if duration is not None or task.due_date else ["start_date"]
        task.save(update_fields=fields)
    return True


def reschedule_successors(task, _seen=None, _depth=0):
    """Push every downstream task so the whole chain stays consistent.

    Returns the tasks that actually moved, so callers can broadcast them.
    """
    from apps.tasks.models import Task

    if _depth > MAX_CASCADE_DEPTH:
        return []
    seen = _seen if _seen is not None else set()
    moved = []

    successor_ids = list(task.successor_links.values_list("successor_id", flat=True))
    if not successor_ids:
        return moved

    successors = Task.objects.filter(id__in=successor_ids).prefetch_related("predecessor_links__predecessor")
    for successor in successors:
        # A diamond-shaped graph legitimately reaches the same task twice; a
        # cycle would too, and this guard covers both.
        if successor.id in seen:
            continue
        seen.add(successor.id)
        if apply_schedule(successor):
            moved.append(successor)
        moved.extend(reschedule_successors(successor, seen, _depth + 1))
    return moved


def would_create_cycle(predecessor, successor):
    """True if linking predecessor -> successor closes a loop.

    A loop makes the schedule unsolvable (each task waiting on the other), so
    the link has to be refused before it is created.
    """
    from apps.tasks.models import TaskDependency

    if predecessor.id == successor.id:
        return True
    # Walk forward from the would-be successor: if we can already reach the
    # predecessor, adding this link closes the circle.
    frontier = {successor.id}
    visited = set()
    while frontier:
        visited |= frontier
        next_ids = set(
            TaskDependency.objects.filter(predecessor_id__in=frontier).values_list("successor_id", flat=True)
        )
        if predecessor.id in next_ids:
            return True
        frontier = next_ids - visited
    return False
