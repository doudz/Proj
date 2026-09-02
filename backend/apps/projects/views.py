from datetime import date

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.cloning import clone_project
from apps.projects.models import (
    DEFAULT_COLUMNS,
    AutomationRule,
    BoardColumn,
    CustomField,
    Label,
    Project,
    ProjectMembership,
)
from apps.projects.permissions import require_project_admin
from apps.projects.serializers import (
    AutomationRuleSerializer,
    BoardColumnSerializer,
    CustomFieldSerializer,
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
        qs = (
            Project.objects.filter(workspace_id__in=user_workspace_ids(self.request.user))
            .prefetch_related("members", "memberships__user", "columns", "labels", "custom_fields")
            .distinct()
        )
        # Templates are blueprints, not work: they stay out of the project lists
        # unless explicitly asked for (?is_template=true). Detail routes still
        # reach them so a template can be opened, edited and instantiated.
        if self.action == "list":
            qs = qs.filter(is_template=self.request.query_params.get("is_template") == "true")
        return qs

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
            # Anyone in the company directory can be added straight to a
            # project; if they are not already in the workspace, being put on
            # one of its projects is reason enough to fold them in as a
            # regular workspace member.
            Membership.objects.get_or_create(
                workspace_id=project.workspace_id, user_id=user_id, defaults={"role": Membership.Role.MEMBER}
            )
            membership, _ = ProjectMembership.objects.update_or_create(
                project=project, user_id=user_id, defaults={"role": role}
            )
            return Response(ProjectMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
        memberships = project.memberships.select_related("user")
        return Response(ProjectMembershipSerializer(memberships, many=True).data)

    @action(detail=True, methods=["post"], url_path="save-as-template")
    def save_as_template(self, request, pk=None):
        """Freeze the project's structure and plan as a reusable blueprint.

        The live project is untouched - the template is a separate copy, so it
        can be curated (renamed tasks, removed noise) without any risk.
        """
        project = self.get_object()
        require_project_admin(request.user, project)
        name = (request.data.get("name") or f"{project.name} (modele)").strip()
        template = clone_project(
            project, name=name, created_by=request.user, is_template=True, keep_assignees=False
        )
        return Response(
            ProjectSerializer(template, context={"request": request}).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="instantiate")
    def instantiate(self, request, pk=None):
        """Create a real project from this template, optionally re-dated.

        Accepts at most one of `start_date` (the plan runs forward from that
        day) or `end_date` (the plan is worked backward so its last task ends
        on that day) - whichever the caller wants to anchor the schedule on.
        """
        template = self.get_object()
        if not template.is_template:
            return Response({"detail": "Ce projet n'est pas un modele."}, status=status.HTTP_400_BAD_REQUEST)
        require_project_admin(request.user, template)
        name = (request.data.get("name") or template.name).strip()
        raw_start = request.data.get("start_date")
        raw_end = request.data.get("end_date")
        if raw_start and raw_end:
            return Response(
                {"detail": "Indiquez soit une date de debut, soit une date de fin, pas les deux."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            start_date = date.fromisoformat(raw_start) if raw_start else None
            end_date = date.fromisoformat(raw_end) if raw_end else None
        except ValueError:
            return Response({"detail": "Date invalide."}, status=status.HTTP_400_BAD_REQUEST)
        project = clone_project(
            template, name=name, created_by=request.user, start_date=start_date, end_date=end_date
        )
        return Response(
            ProjectSerializer(project, context={"request": request}).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, pk=None):
        """Copy the project as a new independent project (plan only, no history)."""
        project = self.get_object()
        require_project_admin(request.user, project)
        name = (request.data.get("name") or f"{project.name} (copie)").strip()
        copy = clone_project(project, name=name, created_by=request.user, is_template=project.is_template)
        return Response(
            ProjectSerializer(copy, context={"request": request}).data, status=status.HTTP_201_CREATED
        )

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


class CustomFieldViewSet(viewsets.ModelViewSet):
    serializer_class = CustomFieldSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["project"]

    def get_queryset(self):
        return CustomField.objects.filter(project__workspace_id__in=user_workspace_ids(self.request.user))

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


class AutomationRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AutomationRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["project"]

    def get_queryset(self):
        return AutomationRule.objects.filter(project__workspace_id__in=user_workspace_ids(self.request.user))

    def perform_create(self, serializer):
        require_project_admin(self.request.user, serializer.validated_data["project"])
        serializer.save()

    def perform_update(self, serializer):
        require_project_admin(self.request.user, serializer.instance.project)
        serializer.save()

    def perform_destroy(self, instance):
        require_project_admin(self.request.user, instance.project)
        instance.delete()
