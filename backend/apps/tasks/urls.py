from rest_framework.routers import DefaultRouter

from apps.tasks.views import (
    AttachmentCommentViewSet,
    AttachmentViewSet,
    CommentViewSet,
    TaskDependencyViewSet,
    TaskViewSet,
    TimeEntryViewSet,
)

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("task-dependencies", TaskDependencyViewSet, basename="task-dependency")
router.register("comments", CommentViewSet, basename="comment")
router.register("attachments", AttachmentViewSet, basename="attachment")
router.register("attachment-comments", AttachmentCommentViewSet, basename="attachment-comment")
router.register("time-entries", TimeEntryViewSet, basename="time-entry")

urlpatterns = router.urls
