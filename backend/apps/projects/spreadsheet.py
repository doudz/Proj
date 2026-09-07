"""Export/import a project's tasks (and project-level custom field values) as
an .xlsx or .ods spreadsheet, so a project can be bulk-edited outside the app
and re-imported to apply the changes.

Two sheets:
- "Taches": one row per task. A fixed set of columns (ID, Titre, Statut...)
  plus one column per task-level custom field, named after the field.
- "Informations projet": one row per project-level custom field, as
  "Champ" / "Valeur" pairs.

Import always targets an existing project (its columns, labels and custom
field definitions decide what a row can reference - none of those are
invented from the file). A row whose "ID" matches an existing task in the
project updates it; any other row (blank or unrecognised ID) creates a new
task. The "ID" column is what makes re-importing an edited export an update
rather than a pile of duplicates.

Not handled by import, on purpose (out of scope for a first version):
dependencies, task hierarchy (subtasks), attachments/comments/history.
"""

import io
from datetime import date, datetime

from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableCell, TableRow
from odf.teletype import extractText
from odf.text import P
from openpyxl import Workbook, load_workbook

TASKS_SHEET = "Taches"
INFO_SHEET = "Informations projet"

FIXED_TASK_COLUMNS = [
    "ID",
    "Titre",
    "Description",
    "Statut",
    "Priorite",
    "Jalon",
    "Debut",
    "Echeance",
    "Avancement",
    "Couleur",
    "Assignes",
    "Externes",
    "Etiquettes",
]

PRIORITY_LABELS = {"low": "Basse", "medium": "Moyenne", "high": "Haute", "urgent": "Urgente"}
PRIORITY_BY_LABEL = {v.lower(): k for k, v in PRIORITY_LABELS.items()}
TRUE_WORDS = {"oui", "vrai", "yes", "true", "1", "x"}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_project(project):
    """Returns (task_headers, task_rows, info_headers, info_rows)."""
    from apps.projects.models import CustomField

    task_fields = list(project.custom_fields.filter(level=CustomField.Level.TASK).order_by("order", "id"))
    project_fields = list(project.custom_fields.filter(level=CustomField.Level.PROJECT).order_by("order", "id"))

    task_headers = [*FIXED_TASK_COLUMNS, *[f.name for f in task_fields]]

    tasks = (
        project.tasks.all()
        .order_by("order", "id")
        .prefetch_related("assignees", "external_assignees", "labels", "custom_values")
    )
    task_rows = []
    for task in tasks:
        custom_by_field = {v.field_id: v.value for v in task.custom_values.all()}
        row = [
            task.id,
            task.title,
            task.description,
            task.column.name if task.column else "",
            PRIORITY_LABELS.get(task.priority, task.priority),
            "Oui" if task.is_milestone else "Non",
            task.start_date,
            task.due_date,
            task.progress,
            task.color,
            ", ".join(a.email for a in task.assignees.all()),
            ", ".join(c.name for c in task.external_assignees.all()),
            ", ".join(l.name for l in task.labels.all()),
        ]
        for field in task_fields:
            raw = custom_by_field.get(field.id, "")
            row.append(_display_custom_value(field, raw))
        task_rows.append(row)

    project_values = {v.field_id: v.value for v in project.custom_values.all()}
    info_headers = ["Champ", "Valeur"]
    info_rows = [[field.name, _display_custom_value(field, project_values.get(field.id, ""))] for field in project_fields]

    return task_headers, task_rows, info_headers, info_rows


def _display_custom_value(field, raw):
    if field.field_type == "checkbox":
        return "Oui" if raw == "true" else "Non"
    return raw


def build_xlsx(project):
    task_headers, task_rows, info_headers, info_rows = export_project(project)
    wb = Workbook()
    ws = wb.active
    ws.title = TASKS_SHEET
    ws.append(task_headers)
    for row in task_rows:
        ws.append(row)

    info_ws = wb.create_sheet(INFO_SHEET)
    info_ws.append(info_headers)
    for row in info_rows:
        info_ws.append(row)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_ods(project):
    task_headers, task_rows, info_headers, info_rows = export_project(project)
    doc = OpenDocumentSpreadsheet()
    _add_ods_table(doc, TASKS_SHEET, task_headers, task_rows)
    _add_ods_table(doc, INFO_SHEET, info_headers, info_rows)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _add_ods_table(doc, name, headers, rows):
    table = Table(name=name)
    doc.spreadsheet.addElement(table)
    table.addElement(_ods_row(headers))
    for row in rows:
        table.addElement(_ods_row(row))


def _ods_row(values):
    tr = TableRow()
    for value in values:
        tr.addElement(_ods_cell(value))
    return tr


def _ods_cell(value):
    if value is None or value == "":
        return TableCell()
    if isinstance(value, bool):
        cell = TableCell(valuetype="boolean", booleanvalue=str(value).lower())
    elif isinstance(value, (int, float)):
        cell = TableCell(valuetype="float", value=value)
    elif isinstance(value, (date, datetime)):
        iso = value.isoformat()
        cell = TableCell(valuetype="date", datevalue=iso)
        cell.addElement(P(text=iso))
        return cell
    else:
        cell = TableCell(valuetype="string")
    cell.addElement(P(text=str(value)))
    return cell


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
def read_spreadsheet(file_obj, filename):
    """Returns {sheet_name: [ [cell, cell, ...], ... ]} - first row of each
    sheet is the header row, values are left as loosely-typed as the format
    gives them (str/int/float/date)."""
    lower = (filename or "").lower()
    if lower.endswith(".ods"):
        return _read_ods(file_obj)
    return _read_xlsx(file_obj)


def _read_xlsx(file_obj):
    wb = load_workbook(file_obj, data_only=True)
    sheets = {}
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            if all(cell is None for cell in row):
                continue
            rows.append(list(row))
        sheets[ws.title] = rows
    return sheets


def _read_ods(file_obj):
    doc = load(file_obj)
    sheets = {}
    for table in doc.spreadsheet.getElementsByType(Table):
        name = table.getAttribute("name")
        rows = []
        for tr in table.getElementsByType(TableRow):
            row = []
            for tc in tr.getElementsByType(TableCell):
                repeat = int(tc.getAttribute("numbercolumnsrepeated") or 1)
                text = extractText(tc)
                row.extend([text] * repeat)
            if any((c or "").strip() for c in row if isinstance(c, str)) or any(
                c not in (None, "") for c in row if not isinstance(c, str)
            ):
                rows.append(row)
        sheets[name] = rows
    return sheets


def import_project(project, file_obj, filename, user):
    """Upserts tasks (matched by the "ID" column) and project-level custom
    field values from the parsed spreadsheet. Returns a report dict:
    {"created": n, "updated": n, "warnings": [str, ...]}."""
    from apps.projects.models import CustomField
    from apps.tasks.models import Task
    from apps.tasks.scheduling import apply_schedule
    from apps.workspaces.models import ExternalContact, Membership

    sheets = read_spreadsheet(file_obj, filename)
    warnings = []
    created = 0
    updated = 0

    columns_by_name = {c.name.strip().lower(): c for c in project.columns.all()}
    labels_by_name = {l.name.strip().lower(): l for l in project.labels.all()}
    task_fields = list(project.custom_fields.filter(level=CustomField.Level.TASK))
    task_field_by_name = {f.name.strip().lower(): f for f in task_fields}
    project_field_by_name = {
        f.name.strip().lower(): f for f in project.custom_fields.filter(level=CustomField.Level.PROJECT)
    }
    member_emails = {
        m.user.email.lower(): m.user for m in Membership.objects.filter(workspace=project.workspace).select_related("user")
    }
    contacts_by_name = {
        c.name.strip().lower(): c for c in ExternalContact.objects.filter(workspace=project.workspace)
    }
    default_column = min(project.columns.all(), key=lambda c: c.order, default=None)

    task_rows = sheets.get(TASKS_SHEET, [])
    if task_rows:
        header = [str(h or "").strip() for h in task_rows[0]]
        index = {name: i for i, name in enumerate(header)}
        missing = [c for c in FIXED_TASK_COLUMNS if c not in index]
        if missing:
            warnings.append(
                f"Feuille « {TASKS_SHEET} » : colonnes manquantes ignorees ({', '.join(missing)})."
            )
        extra_field_columns = [h for h in header if h not in FIXED_TASK_COLUMNS and h]
        unmatched_columns = [h for h in extra_field_columns if h.strip().lower() not in task_field_by_name]
        if unmatched_columns:
            warnings.append(
                "Colonnes non reconnues (aucun champ personnalise de ce nom sur le projet) : "
                + ", ".join(unmatched_columns)
            )

        for row_num, row in enumerate(task_rows[1:], start=2):
            get = lambda name: row[index[name]] if name in index and index[name] < len(row) else None  # noqa: E731
            title = _text(get("Titre"))
            if not title:
                if any(_text(get(c)) for c in FIXED_TASK_COLUMNS if c != "ID"):
                    warnings.append(f"Ligne {row_num} : titre manquant, ligne ignoree.")
                continue

            task_id = get("ID")
            task = None
            if task_id not in (None, ""):
                try:
                    task = project.tasks.get(id=int(task_id))
                except (ValueError, TypeError, Task.DoesNotExist):
                    warnings.append(f"Ligne {row_num} : ID « {task_id} » introuvable dans ce projet, une nouvelle tache sera creee.")

            status_name = _text(get("Statut"))
            column = columns_by_name.get(status_name.lower()) if status_name else None
            if status_name and not column:
                warnings.append(f"Ligne {row_num} : statut « {status_name} » inconnu, colonne inchangee/par defaut.")

            priority_raw = _text(get("Priorite")).lower()
            priority = PRIORITY_BY_LABEL.get(priority_raw) or (priority_raw if priority_raw in PRIORITY_LABELS else None)

            is_milestone = _parse_bool(get("Jalon"))
            start_date = _parse_date(get("Debut"))
            due_date = _parse_date(get("Echeance"))
            progress = _parse_int(get("Avancement"), row_num, "Avancement", warnings)
            color = _text(get("Couleur"))

            if task is None:
                task = Task(project=project, created_by=user, column=column or default_column)
                created += 1
            else:
                updated += 1
                if column:
                    task.column = column

            task.title = title
            task.description = _text(get("Description"))
            if get("Debut") is not None:
                task.start_date = start_date
            if get("Echeance") is not None:
                task.due_date = due_date
            if progress is not None:
                task.progress = max(0, min(100, progress))
            if priority:
                task.priority = priority
            task.is_milestone = is_milestone
            if color:
                task.color = color
            task.save()
            apply_schedule(task)

            emails = [e.strip().lower() for e in _text(get("Assignes")).split(",") if e.strip()]
            users = []
            for email in emails:
                user_match = member_emails.get(email)
                if user_match:
                    users.append(user_match)
                else:
                    warnings.append(f"Ligne {row_num} : assigne « {email} » introuvable dans l'espace de travail.")
            task.assignees.set(users)

            contact_names = [c.strip().lower() for c in _text(get("Externes")).split(",") if c.strip()]
            contacts = []
            for cname in contact_names:
                contact = contacts_by_name.get(cname)
                if contact:
                    contacts.append(contact)
                else:
                    warnings.append(f"Ligne {row_num} : contact externe « {cname} » introuvable.")
            task.external_assignees.set(contacts)

            label_names = [n.strip().lower() for n in _text(get("Etiquettes")).split(",") if n.strip()]
            labels = []
            for lname in label_names:
                label = labels_by_name.get(lname)
                if label:
                    labels.append(label)
                else:
                    warnings.append(f"Ligne {row_num} : etiquette « {lname} » introuvable.")
            task.labels.set(labels)

            for col_name in extra_field_columns:
                field = task_field_by_name.get(col_name.strip().lower())
                if not field:
                    continue
                value = get(col_name)
                if value is None:
                    continue
                from apps.tasks.models import CustomFieldValue

                stored = _to_field_value(field, value)
                CustomFieldValue.objects.update_or_create(field=field, task=task, defaults={"value": stored})

    info_rows = sheets.get(INFO_SHEET, [])
    if info_rows and len(info_rows) > 1:
        for row_num, row in enumerate(info_rows[1:], start=2):
            if len(row) < 2:
                continue
            field_name = _text(row[0]).strip().lower()
            field = project_field_by_name.get(field_name)
            if not field:
                if field_name:
                    warnings.append(f"« {INFO_SHEET} » ligne {row_num} : champ de projet « {row[0]} » introuvable.")
                continue
            from apps.projects.models import ProjectCustomFieldValue

            stored = _to_field_value(field, row[1])
            ProjectCustomFieldValue.objects.update_or_create(
                field=field, project=project, defaults={"value": stored}
            )

    return {"created": created, "updated": updated, "warnings": warnings}


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _parse_bool(value):
    return _text(value).lower() in TRUE_WORDS


def _parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_int(value, row_num, label, warnings):
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        warnings.append(f"Ligne {row_num} : valeur « {value} » invalide pour {label}, ignoree.")
        return None


def _to_field_value(field, raw):
    if field.field_type == "checkbox":
        return "true" if _parse_bool(raw) else "false"
    if isinstance(raw, (date, datetime)):
        return raw.isoformat() if not isinstance(raw, datetime) else raw.date().isoformat()
    return _text(raw)
