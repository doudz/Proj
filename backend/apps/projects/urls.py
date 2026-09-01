from rest_framework.routers import DefaultRouter

from apps.projects.views import BoardColumnViewSet, LabelViewSet, ProjectViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("board-columns", BoardColumnViewSet, basename="board-column")
router.register("labels", LabelViewSet, basename="label")

urlpatterns = router.urls
