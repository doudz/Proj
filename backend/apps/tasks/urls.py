from rest_framework.routers import DefaultRouter

from apps.tasks.views import AttachmentViewSet, CommentViewSet, TaskDependencyViewSet, TaskViewSet

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("task-dependencies", TaskDependencyViewSet, basename="task-dependency")
router.register("comments", CommentViewSet, basename="comment")
router.register("attachments", AttachmentViewSet, basename="attachment")

urlpatterns = router.urls
