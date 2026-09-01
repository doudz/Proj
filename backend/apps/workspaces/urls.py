from rest_framework.routers import DefaultRouter

from apps.workspaces.views import ExternalContactViewSet, WorkspaceViewSet

router = DefaultRouter()
router.register("workspaces", WorkspaceViewSet, basename="workspace")
router.register("external-contacts", ExternalContactViewSet, basename="external-contact")

urlpatterns = router.urls
