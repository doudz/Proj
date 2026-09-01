from django.urls import re_path

from apps.chat.consumers import ProjectConsumer, TaskChatConsumer

websocket_urlpatterns = [
    re_path(r"^ws/projects/(?P<project_id>\d+)/$", ProjectConsumer.as_asgi()),
    re_path(r"^ws/tasks/(?P<task_id>\d+)/chat/$", TaskChatConsumer.as_asgi()),
]
