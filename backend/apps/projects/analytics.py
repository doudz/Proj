from datetime import date, timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project
from apps.workspaces.permissions import user_workspace_ids

TREND_DAYS = 30
UPCOMING_DAYS = 7
UPCOMING_LIMIT = 12

PRIORITY_LABELS = {"low": "Basse", "medium": "Moyenne", "high": "Haute", "urgent": "Urgente"}
PRIORITY_COLORS = {"low": "#90A4AE", "medium": "#42A5F5", "high": "#FFA726", "urgent": "#EF5350"}


class DashboardView(APIView):
    """Aggregated figures for the whole workspace (or one project).

    Everything is computed from the tasks the caller is allowed to see, so the
    numbers always match what they would get by browsing the projects by hand.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.tasks.models import Task
        from apps.tasks.serializers import TaskSerializer

        today = date.today()
        projects = Project.objects.filter(
            workspace_id__in=user_workspace_ids(request.user), is_template=False
        )
        workspace_id = request.query_params.get("workspace")
        if workspace_id:
            projects = projects.filter(workspace_id=workspace_id)
        project_id = request.query_params.get("project")
        if project_id:
            projects = projects.filter(id=project_id)

        tasks = Task.objects.filter(project__in=projects)
        open_q = ~Q(progress=100)
        late_q = Q(due_date__lt=today) & open_q

        totals = tasks.aggregate(
            total=Count("id"),
            done=Count("id", filter=Q(progress=100)),
            late=Count("id", filter=late_q),
            in_progress=Count("id", filter=Q(progress__gt=0) & open_q),
            not_started=Count("id", filter=Q(progress=0)),
            unscheduled=Count("id", filter=Q(start_date__isnull=True) | Q(due_date__isnull=True)),
            due_soon=Count("id", filter=Q(due_date__gte=today, due_date__lte=today + timedelta(days=UPCOMING_DAYS)) & open_q),
            milestones=Count("id", filter=Q(is_milestone=True)),
        )
        totals["projects"] = projects.count()

        by_status = [
            {
                "name": row["column__name"] or "Sans statut",
                "color": row["column__color"] or "#CFD8DC",
                "count": row["count"],
            }
            for row in tasks.values("column__name", "column__color")
            .annotate(count=Count("id"))
            .order_by("-count")
        ]

        by_priority = [
            {
                "priority": row["priority"],
                "label": PRIORITY_LABELS.get(row["priority"], row["priority"]),
                "color": PRIORITY_COLORS.get(row["priority"], "#90A4AE"),
                "count": row["count"],
            }
            for row in tasks.values("priority").annotate(count=Count("id")).order_by("-count")
        ]

        by_assignee = [
            {
                "user_id": row["assignees__id"],
                "name": (
                    f"{row['assignees__first_name']} {row['assignees__last_name']}".strip()
                    if row["assignees__id"]
                    else "Non assignee"
                ),
                "color": row["assignees__avatar_color"] or "#B0BEC5",
                "total": row["total"],
                "open": row["open_count"],
                "late": row["late_count"],
            }
            for row in tasks.values(
                "assignees__id", "assignees__first_name", "assignees__last_name", "assignees__avatar_color"
            )
            .annotate(
                total=Count("id", distinct=True),
                open_count=Count("id", filter=open_q, distinct=True),
                late_count=Count("id", filter=late_q, distinct=True),
            )
            .order_by("-total")
        ]

        by_project = [
            {
                "id": row["id"],
                "name": row["name"],
                "color": row["color"],
                "icon": row["icon"],
                "total": row["total"],
                "done": row["done"],
                "late": row["late_count"],
                "progress": round(row["done"] / row["total"] * 100) if row["total"] else 0,
            }
            for row in projects.values("id", "name", "color", "icon")
            .annotate(
                total=Count("tasks"),
                done=Count("tasks", filter=Q(tasks__progress=100)),
                late_count=Count("tasks", filter=Q(tasks__due_date__lt=today) & ~Q(tasks__progress=100)),
            )
            .order_by("-total")
        ]

        trend_start = today - timedelta(days=TREND_DAYS - 1)
        completed_by_day = {
            row["actual_end_date"]: row["count"]
            for row in tasks.filter(actual_end_date__gte=trend_start, actual_end_date__lte=today)
            .values("actual_end_date")
            .annotate(count=Count("id"))
        }
        created_by_day = {
            row["day"]: row["count"]
            for row in tasks.filter(created_at__date__gte=trend_start)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        }
        trend = []
        for offset in range(TREND_DAYS):
            day = trend_start + timedelta(days=offset)
            trend.append(
                {
                    "date": day.isoformat(),
                    "completed": completed_by_day.get(day, 0),
                    "created": created_by_day.get(day, 0),
                }
            )

        upcoming_qs = (
            tasks.filter(due_date__gte=today, due_date__lte=today + timedelta(days=UPCOMING_DAYS))
            .exclude(progress=100)
            .select_related("project", "column", "project__workspace")
            .prefetch_related("assignees", "external_assignees", "labels", "predecessor_links")
            .order_by("due_date")[:UPCOMING_LIMIT]
        )
        overdue_qs = (
            tasks.filter(due_date__lt=today)
            .exclude(progress=100)
            .select_related("project", "column", "project__workspace")
            .prefetch_related("assignees", "external_assignees", "labels", "predecessor_links")
            .order_by("due_date")[:UPCOMING_LIMIT]
        )
        context = {"request": request}

        return Response(
            {
                "totals": totals,
                "by_status": by_status,
                "by_priority": by_priority,
                "by_assignee": by_assignee,
                "by_project": by_project,
                "trend": trend,
                "upcoming": TaskSerializer(upcoming_qs, many=True, context=context).data,
                "overdue": TaskSerializer(overdue_qs, many=True, context=context).data,
            }
        )
