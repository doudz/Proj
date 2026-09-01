from rest_framework.routers import DefaultRouter

from apps.workspaces.views import WorkspaceViewSet

router = DefaultRouter()
router.register("workspaces", WorkspaceViewSet, basename="workspace")

urlpatterns = router.urls
