import contextvars

# Populated by apps.mcpserver.asgi.McpASGIApp for the duration of one MCP
# HTTP request, from the bearer token it resolved - lets every tool function
# find out who it's acting on behalf of without threading a user argument
# through FastMCP's own call machinery.
_current_user_var = contextvars.ContextVar("mcp_current_user", default=None)


def get_current_user():
    user = _current_user_var.get()
    if user is None:
        raise RuntimeError("Aucun utilisateur authentifie dans le contexte MCP.")
    return user


def set_current_user(user):
    return _current_user_var.set(user)


def reset_current_user(token):
    _current_user_var.reset(token)
