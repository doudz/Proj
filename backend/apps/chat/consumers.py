import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BaseGroupConsumer(AsyncJsonWebsocketConsumer):
    group_name = None

    async def connect(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return
        allowed = await self.has_access()
        if not allowed:
            await self.close(code=4003)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add(f"user_{user.id}", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        user = self.scope.get("user")
        if user and user.is_authenticated:
            await self.channel_layer.group_discard(f"user_{user.id}", self.channel_name)

    async def has_access(self):
        return True

    # generic relay handlers -------------------------------------------------
    async def broadcast_event(self, event):
        await self.send_json({"kind": event["event"], "payload": event["payload"]})

    async def chat_message(self, event):
        await self.send_json({"kind": "comment.created", "payload": event["payload"]})

    async def notification_message(self, event):
        await self.send_json({"kind": "notification.created", "payload": event["payload"]})

    async def presence_message(self, event):
        await self.send_json({"kind": "presence", "payload": event["payload"]})


class ProjectConsumer(BaseGroupConsumer):
    """Realtime channel for a project: task board / Gantt updates + presence."""

    async def connect(self):
        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        self.group_name = f"project_{self.project_id}"
        await super().connect()
        if self.scope["user"].is_authenticated:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "presence.message",
                    "payload": {"user_id": self.scope["user"].id, "status": "online"},
                },
            )

    @database_sync_to_async
    def has_access(self):
        from apps.projects.models import Project
        from apps.workspaces.models import Membership

        try:
            project = Project.objects.get(id=self.project_id)
        except Project.DoesNotExist:
            return False
        return Membership.objects.filter(workspace=project.workspace, user=self.scope["user"]).exists()

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "presence.message",
                    "payload": {"user_id": self.scope["user"].id, "status": "typing", "task": content.get("task")},
                },
            )


class TaskChatConsumer(BaseGroupConsumer):
    """Realtime chat / comments thread scoped to a single task."""

    async def connect(self):
        self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
        self.group_name = f"task_{self.task_id}"
        await super().connect()

    @database_sync_to_async
    def has_access(self):
        from apps.tasks.models import Task
        from apps.workspaces.models import Membership

        try:
            task = Task.objects.select_related("project__workspace").get(id=self.task_id)
        except Task.DoesNotExist:
            return False
        return Membership.objects.filter(workspace=task.project.workspace, user=self.scope["user"]).exists()

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "presence.message",
                    "payload": {"user_id": self.scope["user"].id, "status": "typing"},
                },
            )
