"""FastMCP server exposing GanttFlow to AI clients over Streamable HTTP.

Every tool re-dispatches into the existing DRF viewsets (via
APIRequestFactory + force_authenticate) instead of touching the ORM
directly, so an AI-driven action goes through exactly the same permission
checks, activity logging, websocket broadcasts and automation rules as the
same action taken from the web UI - one set of business rules, not two.
"""

from asgiref.sync import sync_to_async
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.mcpserver.context import get_current_user
from apps.projects.views import BoardColumnViewSet, CustomFieldViewSet, ProjectViewSet
from apps.tasks.views import CommentViewSet, TaskViewSet
from apps.workspaces.views import WorkspaceViewSet

_factory = APIRequestFactory()


def _run(user, method, viewset_cls, actions, *, data=None, query=None, pk=None):
    build = getattr(_factory, method.lower())
    if method == "GET":
        request = build("/mcp-internal/", query or {})
    else:
        request = build("/mcp-internal/", data or {}, format="json")
    force_authenticate(request, user=user)
    view = viewset_cls.as_view(actions)
    response = view(request, pk=str(pk)) if pk is not None else view(request)
    if not (200 <= response.status_code < 300):
        detail = response.data
        if isinstance(detail, dict) and "detail" in detail:
            detail = detail["detail"]
        raise ValueError(f"[{response.status_code}] {detail}")
    data = response.data
    # Standard ModelViewSet list() actions go through DRF's global pagination
    # (PageNumberPagination), which wraps the array in {count, next, previous,
    # results}; the custom search/mine actions already return a plain list.
    # Normalize both to {"items": [...]}: FastMCP's unstructured-content
    # conversion splits a bare list/tuple return into one text block per
    # element instead of one block for the whole array, which would silently
    # scatter a list-returning tool's result across several content blocks.
    if isinstance(data, dict) and {"count", "results"} <= data.keys():
        data = data["results"]
    if isinstance(data, list):
        data = {"items": data}
    return data


async def _call(method, viewset_cls, actions, **kwargs):
    user = get_current_user()
    return await sync_to_async(_run)(user, method, viewset_cls, actions, **kwargs)


def _normalize_custom_values(values):
    """Custom field values are always stored as text; a checkbox or switch
    field in particular expects the literal string "true"/"false" (that's
    what the web UI sends and what displays as checked/on). An AI client
    naturally reaches for a JSON boolean instead - normalize it here so both
    work, rather than silently storing Python's str(True) == "True" and
    breaking the checkbox/switch."""
    normalized = {}
    for key, value in values.items():
        if isinstance(value, bool):
            value = "true" if value else "false"
        normalized[str(key)] = value
    return normalized


mcp = FastMCP(
    name="GanttFlow",
    instructions=(
        "Outil de gestion de projet (Kanban, Gantt, taches). Commencez par "
        "list_workspaces puis list_projects pour recuperer les identifiants "
        "avant de creer ou modifier des projets/taches. list_columns donne "
        "les colonnes (statuts) d'un projet, necessaires pour create_task/"
        "move_task. list_custom_fields donne les champs personnalises d'un "
        "projet (niveau tache ou projet) ; set_task_custom_fields et "
        "set_project_custom_fields renseignent leurs valeurs."
    ),
    stateless_http=True,
    json_response=True,
    # FastMCP auto-enables Host/Origin allowlisting ("DNS rebinding
    # protection") whenever it thinks it's bound to 127.0.0.1 - its default,
    # even though we never use that setting (only .streamable_http_app() is
    # called, never .run()). That check runs before our own auth and would
    # reject every request whose Host header isn't literally localhost,
    # which breaks any real deployment reached through a reverse proxy under
    # its own hostname. Every request is already authenticated by bearer
    # token in apps.mcpserver.asgi regardless of Host, so this is redundant
    # here - disable it explicitly rather than try to enumerate hostnames.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
async def whoami() -> dict:
    """Retourne l'utilisateur actuellement authentifie (celui du jeton API utilise)."""
    user = get_current_user()
    return {"id": user.id, "email": user.email, "name": user.get_full_name(), "job_title": user.job_title}


@mcp.tool()
async def list_workspaces() -> dict:
    """Liste les espaces de travail accessibles a l'utilisateur authentifie (cle "items")."""
    return await _call("GET", WorkspaceViewSet, {"get": "list"})


@mcp.tool()
async def list_projects(workspace_id: int, include_templates: bool = False) -> dict:
    """Liste les projets d'un espace de travail (cle "items"), hors modeles sauf include_templates=true."""
    query = {"workspace": workspace_id}
    if include_templates:
        query["is_template"] = "true"
    return await _call("GET", ProjectViewSet, {"get": "list"}, query=query)


@mcp.tool()
async def get_project(project_id: int) -> dict:
    """Recupere le detail complet d'un projet : colonnes, etiquettes, membres, champs personnalises, avancement."""
    return await _call("GET", ProjectViewSet, {"get": "retrieve"}, pk=project_id)


@mcp.tool()
async def create_project(
    workspace_id: int,
    name: str,
    description: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Cree un nouveau projet (statut initial : Brouillon) dans un espace de travail.

    Les dates sont au format AAAA-MM-JJ. Les colonnes de tableau par defaut
    (A faire / En cours / En revue / Termine) sont creees automatiquement.
    """
    data = {"workspace": workspace_id, "name": name, "description": description}
    if start_date:
        data["start_date"] = start_date
    if end_date:
        data["end_date"] = end_date
    return await _call("POST", ProjectViewSet, {"post": "create"}, data=data)


@mcp.tool()
async def update_project(
    project_id: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Met a jour un projet existant (reserve aux administrateurs du projet).

    status: planned (brouillon), active (en cours), on_hold (en pause), done
    (termine) ou archived (archive).
    """
    data = {}
    for key, value in [
        ("name", name),
        ("description", description),
        ("status", status),
        ("start_date", start_date),
        ("end_date", end_date),
    ]:
        if value is not None:
            data[key] = value
    if not data:
        raise ValueError("Aucun champ a mettre a jour.")
    return await _call("PATCH", ProjectViewSet, {"patch": "partial_update"}, data=data, pk=project_id)


@mcp.tool()
async def list_columns(project_id: int) -> dict:
    """Liste (cle "items") les colonnes (statuts) du tableau Kanban d'un projet - utile pour choisir ou placer une tache."""
    return await _call("GET", BoardColumnViewSet, {"get": "list"}, query={"project": project_id})


@mcp.tool()
async def list_tasks(
    project_id: int | None = None,
    workspace_id: int | None = None,
    assignee_id: int | None = None,
    state: str | None = None,
    query: str | None = None,
    limit: int = 50,
) -> dict:
    """Recherche des taches (cle "items"), filtrables et combinables librement.

    state: open, done, late, in_progress, not_started, unscheduled ou
    blocked. Indiquez project_id ou workspace_id pour limiter la recherche.
    """
    params = {"limit": str(limit)}
    if project_id:
        params["projects"] = str(project_id)
    if workspace_id:
        params["workspace"] = str(workspace_id)
    if assignee_id:
        params["assignees"] = str(assignee_id)
    if state:
        params["state"] = state
    if query:
        params["q"] = query
    return await _call("GET", TaskViewSet, {"get": "search"}, query=params)


@mcp.tool()
async def get_task(task_id: int) -> dict:
    """Recupere le detail complet d'une tache."""
    return await _call("GET", TaskViewSet, {"get": "retrieve"}, pk=task_id)


@mcp.tool()
async def list_my_tasks() -> dict:
    """Liste (cle "items") les taches assignees a l'utilisateur authentifie, tous espaces de travail confondus."""
    return await _call("GET", TaskViewSet, {"get": "mine"})


@mcp.tool()
async def create_task(
    project_id: int,
    title: str,
    description: str = "",
    column_id: int | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
    priority: str = "medium",
    is_milestone: bool = False,
    assignee_ids: list | None = None,
) -> dict:
    """Cree une tache dans un projet (reserve aux administrateurs du projet).

    priority: low, medium, high ou urgent. Dates au format AAAA-MM-JJ. Si
    column_id est omis, la tache n'est placee dans aucune colonne (utilisez
    list_columns pour recuperer les identifiants disponibles).
    """
    data = {
        "project": project_id,
        "title": title,
        "description": description,
        "priority": priority,
        "is_milestone": is_milestone,
    }
    if column_id is not None:
        data["column"] = column_id
    if start_date:
        data["start_date"] = start_date
    if due_date:
        data["due_date"] = due_date
    if assignee_ids:
        data["assignee_ids"] = assignee_ids
    return await _call("POST", TaskViewSet, {"post": "create"}, data=data)


@mcp.tool()
async def update_task(
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    column_id: int | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    assignee_ids: list | None = None,
) -> dict:
    """Met a jour les champs structurels d'une tache (reserve aux administrateurs du projet).

    Pour changer seulement l'avancement ou deplacer la tache, preferez
    update_task_progress / move_task, accessibles aussi aux personnes
    assignees a la tache.
    """
    data = {}
    for key, value in [
        ("title", title),
        ("description", description),
        ("start_date", start_date),
        ("due_date", due_date),
        ("priority", priority),
    ]:
        if value is not None:
            data[key] = value
    if column_id is not None:
        data["column"] = column_id
    if assignee_ids is not None:
        data["assignee_ids"] = assignee_ids
    if not data:
        raise ValueError("Aucun champ a mettre a jour.")
    return await _call("PATCH", TaskViewSet, {"patch": "partial_update"}, data=data, pk=task_id)


@mcp.tool()
async def update_task_progress(task_id: int, progress: int) -> dict:
    """Modifie l'avancement d'une tache (0 a 100). Accessible aussi aux personnes assignees a la tache."""
    if not 0 <= progress <= 100:
        raise ValueError("progress doit etre compris entre 0 et 100.")
    return await _call("PATCH", TaskViewSet, {"patch": "partial_update"}, data={"progress": progress}, pk=task_id)


@mcp.tool()
async def move_task(task_id: int, column_id: int) -> dict:
    """Deplace une tache vers une autre colonne (statut) du tableau Kanban. Accessible aussi aux personnes assignees a la tache."""
    return await _call("POST", TaskViewSet, {"post": "move"}, data={"column": column_id}, pk=task_id)


@mcp.tool()
async def start_task(task_id: int) -> dict:
    """Enregistre le demarrage reel d'une tache (date du jour). Accessible aussi aux personnes assignees a la tache."""
    return await _call("POST", TaskViewSet, {"post": "start"}, data={}, pk=task_id)


@mcp.tool()
async def complete_task(task_id: int) -> dict:
    """Marque une tache comme terminee (avancement 100%, date de fin reelle = aujourd'hui). Accessible aussi aux personnes assignees a la tache."""
    return await _call("POST", TaskViewSet, {"post": "complete"}, data={}, pk=task_id)


@mcp.tool()
async def add_comment(task_id: int, body: str) -> dict:
    """Ajoute un commentaire sur une tache (reserve aux administrateurs et membres du projet, pas aux observateurs)."""
    return await _call("POST", CommentViewSet, {"post": "create"}, data={"task": task_id, "body": body})


@mcp.tool()
async def list_custom_fields(project_id: int, level: str | None = None) -> dict:
    """Liste (cle "items") les champs personnalises definis sur un projet.

    level: "task" (champ ajoute a chaque tache du projet) ou "project"
    (champ affiche sur l'entete du projet) pour filtrer ; omis, les deux
    niveaux sont renvoyes. Les valeurs actuelles se lisent via get_task /
    get_project (cle custom_values, associant l'id du champ a sa valeur).
    """
    result = await _call("GET", CustomFieldViewSet, {"get": "list"}, query={"project": project_id})
    if level:
        result["items"] = [f for f in result["items"] if f["level"] == level]
    return result


@mcp.tool()
async def create_custom_field(
    project_id: int,
    name: str,
    field_type: str = "text",
    level: str = "task",
    options: list | None = None,
    show_in_list: bool = False,
) -> dict:
    """Cree un champ personnalise sur un projet (reserve aux administrateurs du projet).

    field_type: text, number, date, select, checkbox, switch (identique a
    checkbox, juste affiche comme un interrupteur) ou url - pour select,
    fournissez `options` (liste des choix possibles). level: "task" (le
    champ s'ajoute a chaque tache du projet ; desactivable tache par tache
    ensuite) ou "project" (le champ vit sur l'entete du projet, une seule
    valeur). show_in_list: pour un champ de niveau "task", lui donne sa
    propre colonne dans la vue liste des taches.
    """
    data = {
        "project": project_id,
        "name": name,
        "field_type": field_type,
        "level": level,
        "show_in_list": show_in_list,
    }
    if options is not None:
        data["options"] = options
    return await _call("POST", CustomFieldViewSet, {"post": "create"}, data=data)


@mcp.tool()
async def update_custom_field(
    field_id: int,
    name: str | None = None,
    options: list | None = None,
    show_in_list: bool | None = None,
) -> dict:
    """Renomme ou ajuste un champ personnalise existant (reserve aux administrateurs du projet).

    Le type (field_type) et le niveau (level) ne sont pas modifiables une
    fois le champ cree - creez un nouveau champ pour en changer.
    """
    data = {}
    if name is not None:
        data["name"] = name
    if options is not None:
        data["options"] = options
    if show_in_list is not None:
        data["show_in_list"] = show_in_list
    if not data:
        raise ValueError("Aucun champ a mettre a jour.")
    return await _call("PATCH", CustomFieldViewSet, {"patch": "partial_update"}, data=data, pk=field_id)


@mcp.tool()
async def set_task_custom_fields(task_id: int, values: dict) -> dict:
    """Renseigne ou modifie les valeurs des champs personnalises (niveau tache) d'une tache.

    Accessible aussi aux personnes assignees a la tache, comme l'avancement
    (pas seulement aux administrateurs du projet). `values` associe l'id du
    champ personnalise (chaine ou nombre - voir list_custom_fields) a sa
    valeur : une chaine pour text/select/url, "AAAA-MM-JJ" pour date, un
    nombre pour number, "true"/"false" (ou un booleen, converti
    automatiquement) pour checkbox/switch.
    """
    data = {"custom_field_values": _normalize_custom_values(values)}
    return await _call("PATCH", TaskViewSet, {"patch": "partial_update"}, data=data, pk=task_id)


@mcp.tool()
async def set_project_custom_fields(project_id: int, values: dict) -> dict:
    """Renseigne ou modifie les valeurs des champs personnalises (niveau projet) d'un projet.

    Reserve aux administrateurs du projet. `values` associe l'id du champ
    personnalise (voir list_custom_fields avec level="project") a sa valeur
    - memes conventions que set_task_custom_fields.
    """
    data = {"custom_field_values": _normalize_custom_values(values)}
    return await _call("PATCH", ProjectViewSet, {"patch": "partial_update"}, data=data, pk=project_id)
