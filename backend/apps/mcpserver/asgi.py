import asyncio
import json

from apps.mcpserver.auth import resolve_bearer_token
from apps.mcpserver.context import reset_current_user, set_current_user
from apps.mcpserver.tools import mcp


class McpASGIApp:
    """Bearer-token authenticated wrapper around the FastMCP Streamable HTTP
    app, mounted at /mcp by config/asgi.py.

    Starts the FastMCP session manager's background task group itself,
    lazily on the first request, instead of relying on the outer ASGI server
    forwarding 'lifespan' protocol events through this project's custom
    Django + Channels composition (daphne's lifespan support next to a
    hand-rolled path router is not something to depend on) - see
    StreamableHTTPSessionManager.run(), which is an async context manager
    meant to stay open for the life of the process either way.
    """

    def __init__(self, server):
        self._server = server
        self._inner = server.streamable_http_app()
        self._lock = asyncio.Lock()
        self._started = False
        # Keeps the session manager's async-generator-based context manager
        # alive for the life of the process: anyio task groups require the
        # same task to enter and exit their cancel scope, so if this were a
        # bare local variable it would get garbage-collected shortly after
        # __aenter__() returns, and the GC's GeneratorExit (thrown from
        # whatever task happens to run it) would then blow up the task group.
        self._session_cm = None

    async def _ensure_started(self):
        if self._started:
            return
        async with self._lock:
            if self._started:
                return
            self._session_cm = self._server.session_manager.run()
            await self._session_cm.__aenter__()
            self._started = True

    async def __call__(self, scope, receive, send):
        await self._ensure_started()
        headers = dict(scope.get("headers") or [])
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        raw_token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""
        user = await resolve_bearer_token(raw_token)
        if user is None:
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b'Bearer realm="ganttflow-mcp"'),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": json.dumps(
                        {
                            "error": "Jeton API invalide ou manquant. "
                            "Fournissez un en-tete Authorization: Bearer <jeton>."
                        }
                    ).encode(),
                }
            )
            return
        token = set_current_user(user)
        try:
            await self._inner(scope, receive, send)
        finally:
            reset_current_user(token)


mcp_asgi_app = McpASGIApp(mcp)
