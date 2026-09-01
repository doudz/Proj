<template>
  <div class="portfolio-gantt d-flex flex-column fill-height">
    <div class="px-4 py-3 portfolio-toolbar">
      <div class="d-flex flex-wrap align-center ga-3">
        <v-select
          v-model="selectedProjectIds"
          :items="projects"
          item-title="name"
          item-value="id"
          label="Projets"
          multiple
          chips
          closable-chips
          density="compact"
          hide-details
          style="max-width: 280px"
        />
        <v-select
          v-model="selectedAssigneeIds"
          :items="availableAssignees"
          item-title="fullName"
          item-value="id"
          label="Assignes"
          multiple
          chips
          closable-chips
          density="compact"
          hide-details
          style="max-width: 260px"
        />
        <v-select
          v-model="selectedLabelNames"
          :items="availableLabels"
          item-title="name"
          item-value="name"
          label="Categories (etiquettes)"
          multiple
          chips
          closable-chips
          density="compact"
          hide-details
          style="max-width: 260px"
        />
        <v-btn-toggle v-model="groupBy" density="compact" mandatory color="primary" variant="outlined">
          <v-btn value="project" size="small">Par projet</v-btn>
          <v-btn value="assignee" size="small">Par assigne</v-btn>
          <v-btn value="label" size="small">Par categorie</v-btn>
        </v-btn-toggle>
        <v-btn-toggle v-model="zoom" density="compact" mandatory color="primary" variant="outlined">
          <v-btn value="day" size="small">Jour</v-btn>
          <v-btn value="week" size="small">Semaine</v-btn>
          <v-btn value="month" size="small">Mois</v-btn>
        </v-btn-toggle>
        <v-btn size="small" variant="tonal" prepend-icon="mdi-calendar-today" @click="scrollToToday">Aujourd'hui</v-btn>
        <v-spacer />
        <div v-if="conflictCount" class="d-flex align-center text-caption text-error">
          <v-icon icon="mdi-alert-decagram-outline" size="16" class="mr-1" />
          {{ conflictCount }} tache(s) en conflit de charge
        </div>
      </div>
    </div>
    <v-divider />

    <div v-if="portfolioStore.loading" class="d-flex justify-center pa-8">
      <v-progress-circular indeterminate color="primary" />
    </div>
    <div v-else-if="!rows.length" class="pa-8 text-center text-medium-emphasis">
      Aucune tache ne correspond aux filtres selectionnes.
    </div>
    <div v-else ref="bodyRef" class="gantt-body flex-grow-1">
      <div class="gantt-left" :style="{ width: leftWidth + 'px' }">
        <div class="gantt-left-header" :style="{ height: headerHeight + 'px' }">Taches ({{ rows.filter((r) => !r.isGroupHeader).length }})</div>
        <div
          v-for="row in rows"
          :key="row.key"
          class="gantt-left-row"
          :class="{ 'group-header-row': row.isGroupHeader }"
          :style="{ height: rowHeight + 'px', paddingLeft: row.isGroupHeader ? '8px' : '28px' }"
        >
          <template v-if="row.isGroupHeader">
            <v-avatar v-if="row.avatarColor" :color="row.avatarColor" size="22" class="mr-2">
              <span class="text-caption text-white">{{ row.avatarInitials }}</span>
            </v-avatar>
            <span class="dot mr-2" v-else-if="row.color" :style="{ backgroundColor: row.color }"></span>
            <span class="text-subtitle-2 font-weight-bold">{{ row.label }}</span>
            <v-chip size="x-small" class="ml-2" variant="flat">{{ row.count }}</v-chip>
          </template>
          <template v-else>
            <v-chip v-if="groupBy !== 'project'" size="x-small" class="mr-1" :color="row.task.projectColor" variant="flat" label>
              {{ row.task.projectName }}
            </v-chip>
            <v-tooltip v-if="conflicts.has(row.task.id)" location="top">
              <template #activator="{ props: tooltipProps }">
                <v-icon v-bind="tooltipProps" icon="mdi-alert-decagram" size="14" color="error" class="mr-1" />
              </template>
              <span>Chevauche : {{ conflicts.get(row.task.id).join(", ") }}</span>
            </v-tooltip>
            <v-icon v-if="row.task.is_blocked" icon="mdi-lock-outline" size="14" color="warning" class="mr-1" />
            <span class="gantt-row-title" @click="openTask(row.task)">{{ row.task.title }}</span>
          </template>
        </div>
      </div>

      <div class="gantt-right-scroll">
        <div class="gantt-right-content" :style="{ width: totalWidth + 'px' }">
          <div class="gantt-header" :style="{ height: headerHeight + 'px' }">
            <div class="gantt-header-top">
              <div v-for="(g, i) in monthGroups" :key="i" class="gantt-month-group" :style="{ width: g.width + 'px' }">
                {{ g.label }}
              </div>
            </div>
            <div v-if="zoom !== 'month'" class="gantt-header-bottom">
              <div v-for="d in dayTicks" :key="d.iso" class="gantt-day-tick" :class="{ weekend: d.weekend }" :style="{ width: dayWidth + 'px' }">
                {{ d.label }}
              </div>
            </div>
          </div>

          <div class="gantt-grid" :style="{ height: rows.length * rowHeight + 'px' }">
            <div
              v-for="d in dayTicks"
              :key="'bg-' + d.iso"
              v-show="zoom !== 'month'"
              class="gantt-grid-col"
              :class="{ weekend: d.weekend }"
              :style="{ left: d.x + 'px', width: dayWidth + 'px' }"
            ></div>
            <div v-if="todayX !== null" class="gantt-today-line" :style="{ left: todayX + 'px' }"></div>

            <template v-for="(row, index) in rows" :key="row.key">
              <div v-if="row.isGroupHeader" class="gantt-group-band" :style="{ top: index * rowHeight + 'px', height: rowHeight + 'px' }"></div>
              <GanttBar
                v-else-if="row.bar"
                :task="row.task"
                :x="row.bar.x"
                :y="index * rowHeight"
                :width="row.bar.width"
                :day-width="dayWidth"
                @click="openTask(row.task)"
                @reschedule="(delta) => onReschedule(row.task, delta)"
              />
              <div v-else-if="!row.isGroupHeader" class="gantt-noschedule" :style="{ top: index * rowHeight + 8 + 'px' }" @click="openTask(row.task)">
                Cliquer pour planifier
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import GanttBar from "@/components/gantt/GanttBar.vue";
import { addDays, diffDays, formatDate, parseDate, ZOOM_LEVELS } from "@/components/gantt/ganttMath";
import { usePortfolioStore } from "@/stores/portfolio";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

const props = defineProps({
  workspaceId: { type: [String, Number], required: true },
  projects: { type: Array, required: true },
});

const portfolioStore = usePortfolioStore();
const router = useRouter();

const zoom = ref("week");
const groupBy = ref("project");
const selectedProjectIds = ref([]);
const selectedAssigneeIds = ref([]);
const selectedLabelNames = ref([]);
const bodyRef = ref(null);

const leftWidth = 300;
const rowHeight = 40;
const headerHeight = 52;
const dayWidth = computed(() => ZOOM_LEVELS[zoom.value].dayWidth);

const MONTH_LABEL = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" });
const DAY_LABEL = new Intl.DateTimeFormat("fr-FR", { day: "2-digit" });

async function load() {
  await portfolioStore.fetchWorkspaceTasks(props.workspaceId);
}

onMounted(load);
watch(() => props.workspaceId, load);
watch(
  () => props.projects,
  (list) => {
    if (!selectedProjectIds.value.length && list.length) {
      selectedProjectIds.value = list.filter((p) => p.status !== "archived").map((p) => p.id);
    }
  },
  { immediate: true }
);

const projectById = computed(() => new Map(props.projects.map((p) => [p.id, p])));

const tasksWithProjectInfo = computed(() =>
  portfolioStore.tasks.map((t) => {
    const project = projectById.value.get(t.project);
    return { ...t, projectName: project?.name || "?", projectColor: project?.color || "#90A4AE" };
  })
);

const availableAssignees = computed(() => {
  const map = new Map();
  for (const t of tasksWithProjectInfo.value) {
    for (const a of t.assignees) {
      if (!map.has(a.id)) map.set(a.id, { ...a, fullName: `${a.first_name} ${a.last_name}`.trim() || a.email });
    }
  }
  return [...map.values()].sort((a, b) => a.fullName.localeCompare(b.fullName));
});

const availableLabels = computed(() => {
  const map = new Map();
  for (const t of tasksWithProjectInfo.value) {
    for (const l of t.labels) {
      if (!map.has(l.name)) map.set(l.name, { name: l.name, color: l.color });
    }
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
});

const filteredTasks = computed(() => {
  const projectSet = new Set(selectedProjectIds.value);
  const assigneeSet = new Set(selectedAssigneeIds.value);
  const labelSet = new Set(selectedLabelNames.value);
  return tasksWithProjectInfo.value.filter((t) => {
    if (projectSet.size && !projectSet.has(t.project)) return false;
    if (assigneeSet.size && !t.assignees.some((a) => assigneeSet.has(a.id))) return false;
    if (labelSet.size && !t.labels.some((l) => labelSet.has(l.name))) return false;
    return true;
  });
});

function rangesOverlap(aStart, aEnd, bStart, bEnd) {
  return aStart <= bEnd && bStart <= aEnd;
}

const conflicts = computed(() => {
  const map = new Map();
  const byAssignee = new Map();
  for (const t of filteredTasks.value) {
    if (!t.start_date || !t.due_date) continue;
    for (const a of t.assignees) {
      if (!byAssignee.has(a.id)) byAssignee.set(a.id, []);
      byAssignee.get(a.id).push(t);
    }
  }
  for (const tasks of byAssignee.values()) {
    for (let i = 0; i < tasks.length; i++) {
      for (let j = i + 1; j < tasks.length; j++) {
        const a = tasks[i];
        const b = tasks[j];
        if (rangesOverlap(a.start_date, a.due_date, b.start_date, b.due_date)) {
          if (!map.has(a.id)) map.set(a.id, []);
          if (!map.has(b.id)) map.set(b.id, []);
          map.get(a.id).push(b.title);
          map.get(b.id).push(a.title);
        }
      }
    }
  }
  return map;
});

const conflictCount = computed(() => conflicts.value.size);

const range = computed(() => {
  const dates = [];
  for (const t of filteredTasks.value) {
    if (t.start_date) dates.push(parseDate(t.start_date));
    if (t.due_date) dates.push(parseDate(t.due_date));
  }
  const today = new Date();
  let min = dates.length ? new Date(Math.min(...dates)) : addDays(today, -7);
  let max = dates.length ? new Date(Math.max(...dates)) : addDays(today, 30);
  min = addDays(min, -4);
  max = addDays(max, 14);
  return { start: min, end: max };
});

const totalDays = computed(() => Math.max(1, diffDays(range.value.start, range.value.end) + 1));
const totalWidth = computed(() => totalDays.value * dayWidth.value);

const monthGroups = computed(() => {
  const groups = [];
  let cursor = new Date(range.value.start);
  for (let i = 0; i < totalDays.value; i++) {
    const label = MONTH_LABEL.format(cursor);
    if (groups.length && groups[groups.length - 1].label === label) {
      groups[groups.length - 1].width += dayWidth.value;
    } else {
      groups.push({ label, width: dayWidth.value });
    }
    cursor = addDays(cursor, 1);
  }
  return groups;
});

const dayTicks = computed(() => {
  const ticks = [];
  let cursor = new Date(range.value.start);
  for (let i = 0; i < totalDays.value; i++) {
    const dow = cursor.getDay();
    ticks.push({
      iso: formatDate(cursor),
      label: zoom.value === "day" ? DAY_LABEL.format(cursor) : "",
      x: i * dayWidth.value,
      weekend: dow === 0 || dow === 6,
    });
    cursor = addDays(cursor, 1);
  }
  return ticks;
});

const todayX = computed(() => {
  const d = diffDays(range.value.start, new Date());
  if (d < 0 || d > totalDays.value) return null;
  return d * dayWidth.value;
});

function computeBar(task) {
  if (!task.start_date || !task.due_date) return null;
  const start = parseDate(task.start_date);
  const due = parseDate(task.due_date);
  const x = diffDays(range.value.start, start) * dayWidth.value;
  const width = Math.max(dayWidth.value, (diffDays(start, due) + 1) * dayWidth.value);
  return { x, width };
}

const rows = computed(() => {
  const out = [];
  if (groupBy.value === "project") {
    for (const project of props.projects) {
      const tasks = filteredTasks.value.filter((t) => t.project === project.id).sort((a, b) => a.order - b.order);
      if (!tasks.length) continue;
      out.push({ key: `p-${project.id}`, isGroupHeader: true, label: project.name, color: project.color, count: tasks.length });
      for (const task of tasks) {
        out.push({ key: `t-${task.id}`, task, bar: computeBar(task) });
      }
    }
  } else if (groupBy.value === "assignee") {
    const byUser = new Map();
    const unassigned = [];
    for (const t of filteredTasks.value) {
      if (!t.assignees.length) {
        unassigned.push(t);
        continue;
      }
      for (const a of t.assignees) {
        if (!byUser.has(a.id)) byUser.set(a.id, { user: a, tasks: [] });
        byUser.get(a.id).tasks.push(t);
      }
    }
    const sorted = [...byUser.values()].sort((a, b) =>
      `${a.user.first_name} ${a.user.last_name}`.localeCompare(`${b.user.first_name} ${b.user.last_name}`)
    );
    for (const { user, tasks } of sorted) {
      out.push({
        key: `u-${user.id}`,
        isGroupHeader: true,
        label: `${user.first_name} ${user.last_name}`.trim() || user.email,
        avatarColor: user.avatar_color,
        avatarInitials: user.initials,
        count: tasks.length,
      });
      for (const task of tasks.sort((a, b) => (a.start_date || "").localeCompare(b.start_date || ""))) {
        out.push({ key: `t-${task.id}-${user.id}`, task, bar: computeBar(task) });
      }
    }
    if (unassigned.length) {
      out.push({ key: "u-none", isGroupHeader: true, label: "Non assigne", count: unassigned.length });
      for (const task of unassigned) out.push({ key: `t-${task.id}`, task, bar: computeBar(task) });
    }
  } else {
    const byLabel = new Map();
    const unlabeled = [];
    for (const t of filteredTasks.value) {
      if (!t.labels.length) {
        unlabeled.push(t);
        continue;
      }
      for (const l of t.labels) {
        if (!byLabel.has(l.name)) byLabel.set(l.name, { label: l, tasks: [] });
        byLabel.get(l.name).tasks.push(t);
      }
    }
    const sorted = [...byLabel.values()].sort((a, b) => a.label.name.localeCompare(b.label.name));
    for (const { label, tasks } of sorted) {
      out.push({ key: `l-${label.name}`, isGroupHeader: true, label: label.name, color: label.color, count: tasks.length });
      for (const task of tasks.sort((a, b) => (a.start_date || "").localeCompare(b.start_date || ""))) {
        out.push({ key: `t-${task.id}-${label.name}`, task, bar: computeBar(task) });
      }
    }
    if (unlabeled.length) {
      out.push({ key: "l-none", isGroupHeader: true, label: "Sans etiquette", count: unlabeled.length });
      for (const task of unlabeled) out.push({ key: `t-${task.id}`, task, bar: computeBar(task) });
    }
  }
  return out;
});

function onReschedule(task, { startDeltaDays, endDeltaDays }) {
  const start = task.start_date ? formatDate(addDays(parseDate(task.start_date), startDeltaDays)) : null;
  const due = task.due_date ? formatDate(addDays(parseDate(task.due_date), endDeltaDays)) : null;
  portfolioStore.rescheduleTask(task.id, start, due);
}

function openTask(task) {
  router.push({ name: "project", params: { id: task.project }, query: { openTask: task.id } });
}

function scrollToToday() {
  if (!bodyRef.value || todayX.value === null) return;
  const scrollEl = bodyRef.value.querySelector(".gantt-right-scroll");
  scrollEl.scrollLeft = Math.max(0, todayX.value - scrollEl.clientWidth / 2);
}
</script>

<style scoped>
.portfolio-toolbar {
  background: white;
}
.gantt-body {
  display: flex;
  overflow-y: auto;
  position: relative;
}
.gantt-left {
  flex: none;
  border-right: 1px solid rgba(0, 0, 0, 0.08);
  background: white;
}
.gantt-left-header {
  position: sticky;
  top: 0;
  z-index: 3;
  background: #fafafa;
  display: flex;
  align-items: center;
  padding-left: 12px;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
.gantt-left-row {
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  white-space: nowrap;
}
.gantt-left-row.group-header-row {
  background: #f5f7fa;
}
.gantt-row-title {
  cursor: pointer;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}
.gantt-row-title:hover {
  text-decoration: underline;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.gantt-right-scroll {
  flex: 1 1 auto;
  overflow-x: auto;
}
.gantt-right-content {
  position: relative;
}
.gantt-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #fafafa;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
.gantt-header-top {
  display: flex;
  height: 26px;
}
.gantt-month-group {
  border-right: 1px solid rgba(0, 0, 0, 0.08);
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  padding-left: 6px;
  text-transform: capitalize;
  overflow: hidden;
  white-space: nowrap;
}
.gantt-header-bottom {
  display: flex;
  height: 26px;
}
.gantt-day-tick {
  border-right: 1px solid rgba(0, 0, 0, 0.05);
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 0, 0, 0.6);
}
.gantt-day-tick.weekend {
  background: rgba(0, 0, 0, 0.03);
}
.gantt-grid {
  position: relative;
}
.gantt-grid-col {
  position: absolute;
  top: 0;
  bottom: 0;
  border-right: 1px solid rgba(0, 0, 0, 0.04);
}
.gantt-grid-col.weekend {
  background: rgba(0, 0, 0, 0.025);
}
.gantt-today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ef5350;
  z-index: 1;
}
.gantt-group-band {
  position: absolute;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.03);
}
.gantt-noschedule {
  position: absolute;
  left: 8px;
  font-size: 11px;
  color: rgba(0, 0, 0, 0.4);
  cursor: pointer;
  border: 1px dashed rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  padding: 2px 8px;
}
</style>
