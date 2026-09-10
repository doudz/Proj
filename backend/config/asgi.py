import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi_app = get_asgi_application()

from apps.chat.middleware import JWTAuthMiddleware  # noqa: E402
from apps.chat.routing import websocket_urlpatterns  # noqa: E402
from apps.mcpserver.asgi import mcp_asgi_app  # noqa: E402


class HttpPathRouter:
    """Dispatches HTTP requests by path prefix: the MCP connector's own ASGI
    app for /mcp (it needs to own that route outside of Django/DRF - see
    apps.mcpserver.asgi), Django's ASGI app for everything else."""

    def __init__(self, prefix, prefixed_app, default_app):
        self.prefix = prefix
        self.prefixed_app = prefixed_app
        self.default_app = default_app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if path == self.prefix or path.startswith(self.prefix + "/"):
            await self.prefixed_app(scope, receive, send)
        else:
            await self.default_app(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": HttpPathRouter("/mcp", mcp_asgi_app, django_asgi_app),
        "websocket": JWTAuthMiddleware(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
    }
)
