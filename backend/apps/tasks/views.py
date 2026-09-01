from datetime import date

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.projects.permissions import (
    can_edit_task_state,
    require_comment_permission,
    require_project_admin,
    require_task_state_permission,
)
from apps.tasks.models import ActivityLog, Attachment, Comment, Task, TaskDependency
from apps.tasks.scheduling import apply_schedule, reschedule_successors, would_create_cycle
from apps.tasks.serializers import (
    ActivityLogSerializer,
    AttachmentSerializer,
    CommentSerializer,
    TaskDependencySerializer,
    TaskSerializer,
)
from apps.workspaces.permissions import user_workspace_ids


def log_activity(task, user, verb, meta=None):
    ActivityLog.objects.create(task=task, user=user, verb=verb, meta=meta or {})


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["project", "column", "parent", "priority"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        qs = Task.objects.filter(project__workspace_id__in=user_workspace_ids(self.request.user))
        qs = qs.select_related("column", "project", "project__workspace").prefetch_related(
            "assignees", "external_assignees", "labels", "predecessor_links__predecessor", "custom_values"
        )
        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            # Cross-project fetch for the portfolio Gantt - the base queryset above
            # already restricts to workspaces the user belongs to, so this can only narrow it.
            qs = qs.filter(project__workspace_id=workspace_id)
        if self.request.query_params.get("root_only") == "true":
            qs = qs.filter(parent__isnull=True)
        return qs.distinct()

    def perform_create(self, serializer):
        require_project_admin(self.request.user, serializer.validated_data["project"])
        task = serializer.save()
        log_activity(task, self.request.user, "a cree la tache")
        self._broadcast(task.project_id, "task.created", TaskSerializer(task).data)

    def perform_update(self, serializer):
        task = serializer.instance
        changed_fields = set(self.request.data.keys())
        require_task_state_permission(self.request.user, task, changed_fields)
        task = serializer.save()
        # Dependencies own the start date, so re-snap this task and drag the
        # rest of the chain along with it.
        apply_schedule(task)
        log_activity(task, self.request.user, "a modifie la tache")
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)
        self._broadcast_moved(reschedule_successors(task))

    def perform_destroy(self, instance):
        require_project_admin(self.request.user, instance.project)
        project_id = instance.project_id
        task_id = instance.id
        instance.delete()
        self._broadcast(project_id, "task.deleted", {"id": task_id})

    def _broadcast(self, project_id, event_type, payload):
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"project_{project_id}",
            {"type": "broadcast.event", "event": event_type, "payload": payload},
        )

    def _broadcast_moved(self, tasks):
        """Tell every open board about the tasks a cascade just shifted."""
        for task in tasks:
            self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)

    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        """Move a task to a different kanban column / position (drag & drop) -
        a status change, so members may do this on tasks assigned to them."""
        task = self.get_object()
        require_task_state_permission(request.user, task, {"column"})
        column_id = request.data.get("column")
        order = request.data.get("order")
        if column_id is not None:
            task.column_id = column_id
        if order is not None:
            task.order = order
        task.save(update_fields=["column", "order"])
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["post"], url_path="reschedule")
    def reschedule(self, request, pk=None):
        """Update start/due dates - used by the Gantt drag & resize interactions.
        This re-plans the task rather than reporting its state, so it stays an
        admin-only action even for a task's own assignees."""
        task = self.get_object()
        require_project_admin(request.user, task.project)
        start_date = request.data.get("start_date")
        due_date = request.data.get("due_date")
        if start_date:
            task.start_date = date.fromisoformat(start_date)
        if due_date:
            task.due_date = date.fromisoformat(due_date)
        task.save(update_fields=["start_date", "due_date"])
        # The dependencies have the last word on where this task starts.
        apply_schedule(task)
        log_activity(task, request.user, "a replanifie la tache", {"start_date": start_date, "due_date": due_date})
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)
        self._broadcast_moved(reschedule_successors(task))
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["get"], url_path="activity")
    def activity(self, request, pk=None):
        task = self.get_object()
        return Response(ActivityLogSerializer(task.activity.all()[:50], many=True).data)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """Advanced search across every project the user can see.

        All criteria are optional and combine with AND; multi-valued ones
        (projects, assignees, labels, priorities, statuses) are comma-separated
        lists that match any of their values.
        """
        # Template projects are blueprints, not work in progress - their tasks
        # would only be noise here (they are still reachable by opening the
        # template itself).
        qs = self.get_queryset().filter(project__is_template=False)
        params = request.query_params

        def id_list(name):
            raw = params.get(name, "")
            return [int(value) for value in raw.split(",") if value.strip().isdigit()]

        def value_list(name):
            raw = params.get(name, "")
            return [value.strip() for value in raw.split(",") if value.strip()]

        text = params.get("q", "").strip()
        if text:
            qs = qs.filter(
                Q(title__icontains=text)
                | Q(description__icontains=text)
                | Q(custom_values__value__icontains=text)
            )

        workspace_id = params.get("workspace")
        if workspace_id:
            qs = qs.filter(project__workspace_id=workspace_id)
        project_ids = id_list("projects")
        if project_ids:
            qs = qs.filter(project_id__in=project_ids)
        assignee_ids = id_list("assignees")
        if assignee_ids:
            qs = qs.filter(assignees__id__in=assignee_ids)
        label_ids = id_list("labels")
        if label_ids:
            qs = qs.filter(labels__id__in=label_ids)
        column_ids = id_list("columns")
        if column_ids:
            qs = qs.filter(column_id__in=column_ids)
        priorities = value_list("priorities")
        if priorities:
            qs = qs.filter(priority__in=priorities)

        if params.get("unassigned") == "true":
            qs = qs.filter(assignees__isnull=True, external_assignees__isnull=True)
        if params.get("milestones_only") == "true":
            qs = qs.filter(is_milestone=True)

        for param, lookup in [
            ("due_after", "due_date__gte"),
            ("due_before", "due_date__lte"),
            ("start_after", "start_date__gte"),
            ("start_before", "start_date__lte"),
        ]:
            raw = params.get(param)
            if raw:
                try:
                    qs = qs.filter(**{lookup: date.fromisoformat(raw)})
                except ValueError:
                    return Response({"detail": f"Date invalide pour {param}."}, status=status.HTTP_400_BAD_REQUEST)

        state = params.get("state")
        today = date.today()
        if state == "done":
            qs = qs.filter(progress=100)
        elif state == "open":
            qs = qs.exclude(progress=100)
        elif state == "late":
            qs = qs.filter(due_date__lt=today).exclude(progress=100)
        elif state == "in_progress":
            qs = qs.filter(progress__gt=0).exclude(progress=100)
        elif state == "not_started":
            qs = qs.filter(progress=0)
        elif state == "unscheduled":
            qs = qs.filter(Q(start_date__isnull=True) | Q(due_date__isnull=True))
        elif state == "blocked":
            qs = qs.filter(predecessor_links__enforce_blocking=True).exclude(
                predecessor_links__predecessor__progress=100
            )

        ordering = params.get("ordering") or "due_date"
        allowed_ordering = {
            "due_date", "-due_date", "start_date", "-start_date", "title", "-title",
            "priority", "-priority", "progress", "-progress", "created_at", "-created_at",
        }
        if ordering not in allowed_ordering:
            ordering = "due_date"

        qs = qs.distinct().order_by(ordering)
        limit = min(int(params.get("limit") or 200), 500)
        return Response(TaskSerializer(qs[:limit], many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        """Every task assigned to the current user, across all of their workspaces -
        powers the personal "my tasks" home page."""
        qs = self.get_queryset().filter(assignees=request.user).order_by("due_date", "order")
        return Response(TaskSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        """Record the real start date - independent from the planned start_date,
        so a task can be marked as started before or after it was scheduled."""
        task = self.get_object()
        require_task_state_permission(request.user, task, {"actual_start_date"})
        if not request.data.get("force") and task.is_blocked():
            blockers = ", ".join(t.title for t in task.blocking_predecessor_tasks())
            return Response(
                {"detail": f"Cette tache est bloquee par une dependance non terminee : {blockers}."},
                status=status.HTTP_409_CONFLICT,
            )
        raw_date = request.data.get("date")
        task.actual_start_date = date.fromisoformat(raw_date) if raw_date else date.today()
        task.save(update_fields=["actual_start_date"])
        log_activity(task, request.user, "a demarre la tache", {"actual_start_date": str(task.actual_start_date)})
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Record the real finish date and mark the task done - independent from
        the planned due_date, so it can be completed before or after schedule."""
        task = self.get_object()
        require_task_state_permission(request.user, task, {"actual_end_date", "progress"})
        raw_date = request.data.get("date")
        task.actual_end_date = date.fromisoformat(raw_date) if raw_date else date.today()
        task.progress = 100
        task.save(update_fields=["actual_end_date", "progress"])
        log_activity(task, request.user, "a termine la tache", {"actual_end_date": str(task.actual_end_date)})
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)
        return Response(TaskSerializer(task).data)


class TaskDependencyViewSet(viewsets.ModelViewSet):
    serializer_class = TaskDependencySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["predecessor", "successor"]

    def get_queryset(self):
        return TaskDependency.objects.filter(
            predecessor__project__workspace_id__in=user_workspace_ids(self.request.user)
        )

    def create(self, request, *args, **kwargs):
        if int(request.data.get("predecessor")) == int(request.data.get("successor")):
            return Response({"detail": "Une tache ne peut pas dependre d'elle-meme."}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        predecessor = serializer.validated_data["predecessor"]
        successor = serializer.validated_data["successor"]
        require_project_admin(self.request.user, predecessor.project)
        # A circular chain has no solvable schedule - each task would wait on
        # the other - so the link is refused rather than silently ignored.
        if would_create_cycle(predecessor, successor):
            raise ValidationError(
                {"detail": "Cette dependance creerait un cycle : la tache precedente depend deja de la suivante."}
            )
        dependency = serializer.save()
        self._apply_and_broadcast(dependency.successor)

    def perform_update(self, serializer):
        require_project_admin(self.request.user, serializer.instance.predecessor.project)
        dependency = serializer.save()
        self._apply_and_broadcast(dependency.successor)

    def perform_destroy(self, instance):
        require_project_admin(self.request.user, instance.predecessor.project)
        successor = instance.successor
        instance.delete()
        # The successor may now be free (or driven by a different link).
        successor.refresh_from_db()
        self._apply_and_broadcast(successor)

    def _apply_and_broadcast(self, successor):
        """Re-snap the successor onto its links and push the change downstream."""
        moved = []
        if apply_schedule(successor):
            moved.append(successor)
        moved.extend(reschedule_successors(successor))
        layer = get_channel_layer()
        if layer is None:
            return
        for task in moved:
            async_to_sync(layer.group_send)(
                f"project_{task.project_id}",
                {"type": "broadcast.event", "event": "task.updated", "payload": TaskSerializer(task).data},
            )


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["task"]

    def get_queryset(self):
        return Comment.objects.filter(task__project__workspace_id__in=user_workspace_ids(self.request.user))

    def perform_create(self, serializer):
        task = serializer.validated_data["task"]
        require_comment_permission(self.request.user, task.project)
        comment = serializer.save(author=self.request.user)
        log_activity(comment.task, self.request.user, "a commente")
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(
                f"task_{comment.task_id}",
                {"type": "chat.message", "payload": CommentSerializer(comment).data},
            )


class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["task"]

    def get_queryset(self):
        return Attachment.objects.filter(task__project__workspace_id__in=user_workspace_ids(self.request.user))

    def perform_create(self, serializer):
        task = serializer.validated_data["task"]
        if not can_edit_task_state(self.request.user, task):
            raise PermissionDenied("Vous n'avez pas la permission d'ajouter une piece jointe a cette tache.")
        serializer.save(uploaded_by=self.request.user)

    def perform_destroy(self, instance):
        if not can_edit_task_state(self.request.user, instance.task):
            raise PermissionDenied("Vous n'avez pas la permission de supprimer cette piece jointe.")
        instance.delete()
