// Shared with the backend's Project.Status choices (apps/projects/models.py).
export const PROJECT_STATUSES = [
  { title: "Planifie", value: "planned" },
  { title: "En cours", value: "active" },
  { title: "En pause", value: "on_hold" },
  { title: "Termine", value: "done" },
  { title: "Archive", value: "archived" },
];

const COLORS = { planned: "grey", active: "primary", on_hold: "warning", done: "success", archived: "grey-darken-1" };

export function projectStatusLabel(status) {
  return PROJECT_STATUSES.find((s) => s.value === status)?.title || status;
}

export function projectStatusColor(status) {
  return COLORS[status] || "grey";
}
