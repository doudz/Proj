from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
        qs = qs.select_related("column", "project").prefetch_related("assignees", "labels", "predecessor_links")
        if self.request.query_params.get("root_only") == "true":
            qs = qs.filter(parent__isnull=True)
        return qs.distinct()

    def perform_create(self, serializer):
        task = serializer.save()
        log_activity(task, self.request.user, "a cree la tache")
        self._broadcast(task.project_id, "task.created", TaskSerializer(task).data)

    def perform_update(self, serializer):
        task = serializer.save()
        log_activity(task, self.request.user, "a modifie la tache")
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)

    def perform_destroy(self, instance):
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
        """Move a task to a different kanban column / position (drag & drop)."""
        task = self.get_object()
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
        """Update start/due dates - used by the Gantt drag & resize interactions."""
        task = self.get_object()
        start_date = request.data.get("start_date")
        due_date = request.data.get("due_date")
        if start_date:
            task.start_date = start_date
        if due_date:
            task.due_date = due_date
        task.save(update_fields=["start_date", "due_date"])
        log_activity(task, request.user, "a replanifie la tache", {"start_date": start_date, "due_date": due_date})
        self._broadcast(task.project_id, "task.updated", TaskSerializer(task).data)
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["get"], url_path="activity")
    def activity(self, request, pk=None):
        task = self.get_object()
        return Response(ActivityLogSerializer(task.activity.all()[:50], many=True).data)


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


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["task"]

    def get_queryset(self):
        return Comment.objects.filter(task__project__workspace_id__in=user_workspace_ids(self.request.user))

    def perform_create(self, serializer):
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
        serializer.save(uploaded_by=self.request.user)
