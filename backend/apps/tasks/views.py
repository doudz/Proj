from datetime import date

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework.exceptions import PermissionDenied

from apps.projects.permissions import (
    can_edit_task_state,
    require_comment_permission,
    require_project_admin,
    require_task_state_permission,
)
from apps.tasks.models import ActivityLog, Attachment, Comment, Task, TaskDependency
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
            "assignees", "external_assignees", "labels", "predecessor_links"
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
        log_activity(task, self.request.user, "a modifie la tache")
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)

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
        log_activity(task, request.user, "a replanifie la tache", {"start_date": start_date, "due_date": due_date})
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["get"], url_path="activity")
    def activity(self, request, pk=None):
        task = self.get_object()
        return Response(ActivityLogSerializer(task.activity.all()[:50], many=True).data)

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
        require_project_admin(self.request.user, serializer.validated_data["predecessor"].project)
        serializer.save()

    def perform_update(self, serializer):
        require_project_admin(self.request.user, serializer.instance.predecessor.project)
        serializer.save()

    def perform_destroy(self, instance):
        require_project_admin(self.request.user, instance.predecessor.project)
        instance.delete()


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
