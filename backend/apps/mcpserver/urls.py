from rest_framework.routers import DefaultRouter

from apps.mcpserver.views import ApiTokenViewSet

router = DefaultRouter()
router.register("api-tokens", ApiTokenViewSet, basename="api-token")

urlpatterns = router.urls
