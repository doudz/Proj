from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.projects.analytics import DashboardView
from apps.projects.views import BoardColumnViewSet, CustomFieldViewSet, LabelViewSet, ProjectViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("board-columns", BoardColumnViewSet, basename="board-column")
router.register("labels", LabelViewSet, basename="label")
router.register("custom-fields", CustomFieldViewSet, basename="custom-field")

urlpatterns = router.urls + [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
