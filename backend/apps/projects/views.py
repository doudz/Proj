from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.models import DEFAULT_COLUMNS, BoardColumn, Label, Project
from apps.projects.serializers import BoardColumnSerializer, LabelSerializer, ProjectSerializer
from apps.workspaces.permissions import user_workspace_ids


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["workspace", "status"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return (
            Project.objects.filter(workspace_id__in=user_workspace_ids(self.request.user))
            .prefetch_related("members", "columns", "labels")
            .distinct()
        )

    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.save(created_by=self.request.user)
        project.members.add(self.request.user)
        BoardColumn.objects.bulk_create([BoardColumn(project=project, **col) for col in DEFAULT_COLUMNS])

    @action(detail=True, methods=["post"], url_path="reorder-columns")
    def reorder_columns(self, request, pk=None):
        project = self.get_object()
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


class BoardColumnViewSet(viewsets.ModelViewSet):
    serializer_class = BoardColumnSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["project"]

    def get_queryset(self):
        return BoardColumn.objects.filter(project__workspace_id__in=user_workspace_ids(self.request.user))


class LabelViewSet(viewsets.ModelViewSet):
    serializer_class = LabelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["project"]

    def get_queryset(self):
        return Label.objects.filter(project__workspace_id__in=user_workspace_ids(self.request.user))
