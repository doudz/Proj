from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.models import DEFAULT_COLUMNS, BoardColumn, Label, Project, ProjectMembership
from apps.projects.permissions import require_project_admin
from apps.projects.serializers import (
    BoardColumnSerializer,
    LabelSerializer,
    ProjectMembershipSerializer,
    ProjectSerializer,
)
from apps.workspaces.models import Membership
from apps.workspaces.permissions import user_workspace_ids


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["workspace", "status"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return (
            Project.objects.filter(workspace_id__in=user_workspace_ids(self.request.user))
            .prefetch_related("members", "memberships__user", "columns", "labels")
            .distinct()
        )

    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.save(created_by=self.request.user)
        ProjectMembership.objects.create(project=project, user=self.request.user, role=ProjectMembership.Role.ADMIN)
        BoardColumn.objects.bulk_create([BoardColumn(project=project, **col) for col in DEFAULT_COLUMNS])

    def perform_update(self, serializer):
        require_project_admin(self.request.user, serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        require_project_admin(self.request.user, instance)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="reorder-columns")
    def reorder_columns(self, request, pk=None):
        project = self.get_object()
        require_project_admin(request.user, project)
        order = request.data.get("order", [])
        columns = {c.id: c for c in project.columns.all()}
        updated = []
        for index, column_id in enumerate(order):
            column = columns.get(int(column_id))
            if column:
                column.order = index
                updated.append(column)
        BoardColumn.objects.bulk_update(updated, ["order"])
        return Response(BoardColumnSerializer(project.columns.all(), many=True).data)

    @action(detail=True, methods=["post"], url_path="set-baseline")
    @transaction.atomic
    def set_baseline(self, request, pk=None):
        """Freeze the current planned dates (start_date/due_date) of every task
        as the reference plan, so schedule drift can be measured later."""
        project = self.get_object()
        require_project_admin(request.user, project)
        tasks = list(project.tasks.filter(start_date__isnull=False, due_date__isnull=False))
        for task in tasks:
            task.baseline_start_date = task.start_date
            task.baseline_end_date = task.due_date
        from apps.tasks.models import Task

        Task.objects.bulk_update(tasks, ["baseline_start_date", "baseline_end_date"])
        project.baseline_captured_at = timezone.now()
        project.save(update_fields=["baseline_captured_at"])
        self._broadcast_baseline(project.id)
        return Response(ProjectSerializer(project, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="clear-baseline")
    def clear_baseline(self, request, pk=None):
        project = self.get_object()
        require_project_admin(request.user, project)
        project.tasks.update(baseline_start_date=None, baseline_end_date=None)
        project.baseline_captured_at = None
        project.save(update_fields=["baseline_captured_at"])
        self._broadcast_baseline(project.id)
        return Response(ProjectSerializer(project, context={"request": request}).data)

    def _broadcast_baseline(self, project_id):
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"project_{project_id}",
            {"type": "broadcast.event", "event": "baseline.updated", "payload": {"project": project_id}},
        )

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        project = self.get_object()
        if request.method == "POST":
            require_project_admin(request.user, project)
            user_id = request.data.get("user_id")
            role = request.data.get("role", ProjectMembership.Role.MEMBER)
            if role not in ProjectMembership.Role.values:
                return Response({"detail": "Role invalide."}, status=status.HTTP_400_BAD_REQUEST)
            if not Membership.objects.filter(workspace_id=project.workspace_id, user_id=user_id).exists():
                return Response(
                    {"detail": "Cette personne doit d'abord etre membre de l'espace de travail."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            membership, _ = ProjectMembership.objects.update_or_create(
                project=project, user_id=user_id, defaults={"role": role}
            )
            return Response(ProjectMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
        memberships = project.memberships.select_related("user")
        return Response(ProjectMembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=["delete"], url_path="members/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        project = self.get_object()
        require_project_admin(request.user, project)
        project.memberships.filter(user_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BoardColumnViewSet(viewsets.ModelViewSet):
    serializer_class = BoardColumnSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["project"]

    def get_queryset(self):
        return BoardColumn.objects.filter(project__workspace_id__in=user_workspace_ids(self.request.user))

    def perform_create(self, serializer):
        require_project_admin(self.request.user, serializer.validated_data["project"])
        serializer.save()

    def perform_update(self, serializer):
        require_project_admin(self.request.user, serializer.instance.project)
        serializer.save()

    def perform_destroy(self, instance):
        require_project_admin(self.request.user, instance.project)
        instance.delete()


class LabelViewSet(viewsets.ModelViewSet):
    serializer_class = LabelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["project"]

    def get_queryset(self):
        return Label.objects.filter(project__workspace_id__in=user_workspace_ids(self.request.user))

    def perform_create(self, serializer):
        require_project_admin(self.request.user, serializer.validated_data["project"])
        serializer.save()

    def perform_update(self, serializer):
        require_project_admin(self.request.user, serializer.instance.project)
        serializer.save()

    def perform_destroy(self, instance):
        require_project_admin(self.request.user, instance.project)
        instance.delete()
