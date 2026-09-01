<template>
  <div class="gantt-root d-flex flex-column fill-height">
    <div class="d-flex align-center px-4 py-2 gantt-toolbar">
      <v-btn-toggle v-model="zoom" density="compact" mandatory color="primary" variant="outlined">
        <v-btn value="day" size="small">Jour</v-btn>
        <v-btn value="week" size="small">Semaine</v-btn>
        <v-btn value="month" size="small">Mois</v-btn>
      </v-btn-toggle>
      <v-btn class="ml-3" size="small" variant="tonal" prepend-icon="mdi-calendar-today" @click="scrollToToday">Aujourd'hui</v-btn>
      <v-divider vertical class="mx-3" />
      <v-switch
        v-model="showBaseline"
        :disabled="!project.baseline_captured_at"
        label="Comparer a la ligne de base"
        density="compact"
        color="primary"
        hide-details
        class="flex-grow-0"
      />
      <span v-if="project.baseline_captured_at" class="text-caption text-medium-emphasis ml-2">
        capturee le {{ formatCapturedAt(project.baseline_captured_at) }}
      </span>
      <v-btn
        size="small"
        variant="text"
        class="ml-2"
        prepend-icon="mdi-flag-outline"
        @click="confirmBaseline = true"
      >
        {{ project.baseline_captured_at ? "Mettre a jour" : "Definir la ligne de base" }}
      </v-btn>
      <v-btn
        v-if="project.baseline_captured_at"
        size="small"
        variant="text"
        color="error"
        @click="clearBaseline"
      >
        Effacer
      </v-btn>
      <v-spacer />
      <div v-if="showBaseline && project.baseline_captured_at" class="d-flex align-center ga-3 mr-4">
        <span class="d-flex align-center text-caption"><span class="legend-swatch legend-baseline"></span>Ligne de base</span>
        <span class="d-flex align-center text-caption"><span class="legend-swatch legend-actual"></span>Reel</span>
      </div>
      <span class="text-caption text-medium-emphasis">Glissez une barre pour replanifier, tirez ses extremites pour redimensionner</span>
    </div>

    <v-dialog v-model="confirmBaseline" max-width="440">
      <v-card :title="project.baseline_captured_at ? 'Mettre a jour la ligne de base' : 'Definir la ligne de base'">
        <v-card-text>
          Les dates planifiees actuelles (debut/echeance) de chaque tache seront figees comme reference.
          <span v-if="project.baseline_captured_at">La ligne de base precedente sera remplacee.</span>
          Vous pourrez ensuite comparer le reel a cette reference.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmBaseline = false">Annuler</v-btn>
          <v-btn color="primary" @click="applyBaseline">Confirmer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-divider />
    <div ref="bodyRef" class="gantt-body flex-grow-1">
      <div class="gantt-left" :style="{ width: leftWidth + 'px' }">
        <div class="gantt-left-header" :style="{ height: headerHeight + 'px' }">Taches</div>
        <div
          v-for="row in rows"
          :key="row.task.id"
          class="gantt-left-row"
          :style="{ height: rowHeight + 'px', paddingLeft: 8 + row.depth * 18 + 'px' }"
        >
          <v-btn
            v-if="row.hasChildren"
            :icon="collapsed.has(row.task.id) ? 'mdi-chevron-right' : 'mdi-chevron-down'"
            size="x-small"
            variant="text"
            density="compact"
            @click="toggleCollapse(row.task.id)"
          />
          <span v-else class="gantt-leaf-spacer"></span>
          <v-icon v-if="row.task.is_blocked" icon="mdi-lock-outline" size="14" color="warning" class="mr-1" :title="'Bloquee par : ' + row.task.blocking_predecessor_titles.join(', ')" />
          <span class="gantt-row-title" @click="$emit('open-task', row.task.id)">{{ row.task.title }}</span>
          <v-chip size="x-small" class="ml-1" variant="flat">{{ row.task.progress }}%</v-chip>
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
              <div
                v-for="d in dayTicks"
                :key="d.iso"
                class="gantt-day-tick"
                :class="{ weekend: d.weekend, today: d.isToday }"
                :style="{ width: dayWidth + 'px' }"
              >
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

            <svg class="gantt-links" :width="totalWidth" :height="rows.length * rowHeight">
              <defs>
                <marker id="gantt-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                  <path d="M0,0 L0,6 L6,3 z" fill="#90a4ae" />
                </marker>
              </defs>
              <path v-for="link in links" :key="link.id" :d="link.path" class="gantt-link-path" />
            </svg>

            <template v-for="(row, index) in rows" :key="row.task.id">
              <div
                v-if="showBaseline && row.baselineBar"
                class="gantt-baseline-bar"
                :style="{ left: row.baselineBar.x + 'px', top: index * rowHeight + BAR_TOP - 7 + 'px', width: row.baselineBar.width + 'px' }"
                :title="`Ligne de base : ${row.task.baseline_start_date} -> ${row.task.baseline_end_date}`"
              ></div>
              <GanttBar
                v-if="row.bar"
                :task="row.task"
                :x="row.bar.x"
                :y="index * rowHeight"
                :width="row.bar.width"
                :bar-top="BAR_TOP"
                :bar-height="BAR_HEIGHT"
                :day-width="dayWidth"
                @click="$emit('open-task', row.task.id)"
                @reschedule="(delta) => onReschedule(row.task, delta)"
              />
              <div
                v-else
                class="gantt-noschedule"
                :style="{ top: index * rowHeight + 8 + 'px' }"
                @click="$emit('open-task', row.task.id)"
              >
                Cliquer pour planifier
              </div>
              <div
                v-if="showBaseline && row.actualBar"
                class="gantt-actual-bar"
                :class="{ late: row.actualLate, early: row.actualLate === false }"
                :style="{ left: row.actualBar.x + 'px', top: index * rowHeight + BAR_TOP + BAR_HEIGHT + 2 + 'px', width: row.actualBar.width + 'px' }"
                :title="actualTooltip(row.task)"
              ></div>
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
import { useProjectStore } from "@/stores/project";
import { useTaskStore } from "@/stores/task";
import { computed, reactive, ref, watch } from "vue";

const props = defineProps({ project: { type: Object, required: true } });
defineEmits(["open-task"]);

const taskStore = useTaskStore();
const projectStore = useProjectStore();
const zoom = ref("day");
const collapsed = reactive(new Set());
const bodyRef = ref(null);
const showBaseline = ref(!!props.project.baseline_captured_at);
const confirmBaseline = ref(false);

watch(
  () => props.project.baseline_captured_at,
  (value) => {
    if (value) showBaseline.value = true;
  }
);

const leftWidth = 280;
const rowHeight = 48;
const BAR_TOP = 13;
const BAR_HEIGHT = 22;
const headerHeight = 52;
const dayWidth = computed(() => ZOOM_LEVELS[zoom.value].dayWidth);

const MONTH_LABEL = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" });
const DAY_LABEL = new Intl.DateTimeFormat("fr-FR", { day: "2-digit" });

const range = computed(() => {
  const dates = [];
  for (const t of taskStore.tasks) {
    if (t.start_date) dates.push(parseDate(t.start_date));
    if (t.due_date) dates.push(parseDate(t.due_date));
    if (t.baseline_start_date) dates.push(parseDate(t.baseline_start_date));
    if (t.baseline_end_date) dates.push(parseDate(t.baseline_end_date));
    if (t.actual_start_date) dates.push(parseDate(t.actual_start_date));
    if (t.actual_end_date) dates.push(parseDate(t.actual_end_date));
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
  const today = formatDate(new Date());
  let cursor = new Date(range.value.start);
  for (let i = 0; i < totalDays.value; i++) {
    const dow = cursor.getDay();
    ticks.push({
      iso: formatDate(cursor),
      label: zoom.value === "day" ? DAY_LABEL.format(cursor) : "",
      x: i * dayWidth.value,
      weekend: dow === 0 || dow === 6,
      isToday: formatDate(cursor) === today,
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

function hasChildren(id) {
  return taskStore.tasks.some((t) => t.parent === id);
}

const rows = computed(() => {
  const out = [];
  function walk(parentId, depth) {
    const children = taskStore.tasks
      .filter((t) => (t.parent || null) === parentId)
      .sort((a, b) => a.order - b.order);
    for (const task of children) {
      const children_ = hasChildren(task.id);
      out.push({
        task,
        depth,
        hasChildren: children_,
        bar: computeBar(task),
        baselineBar: computeRange(task.baseline_start_date, task.baseline_end_date),
        actualBar: computeRange(task.actual_start_date, task.actual_end_date || (task.actual_start_date ? formatDate(new Date()) : null)),
        actualLate: computeActualLate(task),
      });
      if (children_ && !collapsed.has(task.id)) {
        walk(task.id, depth + 1);
      }
    }
  }
  walk(null, 0);
  return out;
});

function computeBar(task) {
  return computeRange(task.start_date, task.due_date);
}

function computeRange(startIso, endIso) {
  if (!startIso || !endIso) return null;
  const start = parseDate(startIso);
  const end = parseDate(endIso);
  const x = diffDays(range.value.start, start) * dayWidth.value;
  const width = Math.max(dayWidth.value, (diffDays(start, end) + 1) * dayWidth.value);
  return { x, width };
}

function computeActualLate(task) {
  if (!task.baseline_end_date) return null;
  const referenceEnd = task.actual_end_date || (task.actual_start_date ? formatDate(new Date()) : null);
  if (!referenceEnd) return null;
  return parseDate(referenceEnd) > parseDate(task.baseline_end_date);
}

function actualTooltip(task) {
  const start = task.actual_start_date || "?";
  const end = task.actual_end_date || (task.actual_start_date ? "en cours" : "?");
  if (task.end_variance_days === null || task.end_variance_days === undefined) {
    return `Reel : ${start} -> ${end}`;
  }
  const variance = task.end_variance_days;
  const label = variance > 0 ? `retard de ${variance} j` : variance < 0 ? `avance de ${-variance} j` : "a l'heure";
  return `Reel : ${start} -> ${end} (${label} vs ligne de base)`;
}

function formatCapturedAt(value) {
  return new Date(value).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
}

async function applyBaseline() {
  await projectStore.setBaseline(props.project.id);
  await taskStore.fetchTasks(props.project.id);
  confirmBaseline.value = false;
  showBaseline.value = true;
}

async function clearBaseline() {
  await projectStore.clearBaseline(props.project.id);
  await taskStore.fetchTasks(props.project.id);
  showBaseline.value = false;
}

const links = computed(() => {
  const rowIndexByTask = new Map(rows.value.map((r, i) => [r.task.id, i]));
  const paths = [];
  for (const dep of taskStore.dependencies) {
    const predIdx = rowIndexByTask.get(dep.predecessor);
    const succIdx = rowIndexByTask.get(dep.successor);
    if (predIdx === undefined || succIdx === undefined) continue;
    const predBar = rows.value[predIdx].bar;
    const succBar = rows.value[succIdx].bar;
    if (!predBar || !succBar) continue;
    const x1 = predBar.x + predBar.width;
    const y1 = predIdx * rowHeight + rowHeight / 2;
    const x2 = succBar.x;
    const y2 = succIdx * rowHeight + rowHeight / 2;
    const midX = x1 + Math.max(16, (x2 - x1) / 2);
    const path =
      x2 >= x1 + 8
        ? `M ${x1} ${y1} H ${midX} V ${y2} H ${x2}`
        : `M ${x1} ${y1} H ${x1 + 16} V ${y1 + rowHeight / 2} H ${x2 - 16} V ${y2} H ${x2}`;
    paths.push({ id: dep.id, path });
  }
  return paths;
});

function toggleCollapse(id) {
  if (collapsed.has(id)) collapsed.delete(id);
  else collapsed.add(id);
}

function onReschedule(task, { startDeltaDays, endDeltaDays }) {
  const start = task.start_date ? formatDate(addDays(parseDate(task.start_date), startDeltaDays)) : null;
  const due = task.due_date ? formatDate(addDays(parseDate(task.due_date), endDeltaDays)) : null;
  taskStore.rescheduleTask(task.id, start, due);
}

function scrollToToday() {
  if (!bodyRef.value || todayX.value === null) return;
  const scrollEl = bodyRef.value.querySelector(".gantt-right-scroll");
  scrollEl.scrollLeft = Math.max(0, todayX.value - scrollEl.clientWidth / 2);
}
</script>

<style scoped>
.gantt-toolbar {
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
.gantt-leaf-spacer {
  width: 28px;
  display: inline-block;
}
.gantt-row-title {
  cursor: pointer;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 170px;
}
.gantt-row-title:hover {
  text-decoration: underline;
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
.gantt-day-tick.today {
  font-weight: 700;
  color: #1976d2;
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
.gantt-links {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}
.gantt-link-path {
  fill: none;
  stroke: #90a4ae;
  stroke-width: 1.5;
  marker-end: url(#gantt-arrow);
}
.gantt-baseline-bar {
  position: absolute;
  height: 6px;
  border-radius: 3px;
  background: repeating-linear-gradient(45deg, #b0bec5, #b0bec5 4px, #cfd8dc 4px, #cfd8dc 8px);
  opacity: 0.9;
}
.gantt-actual-bar {
  position: absolute;
  height: 6px;
  border-radius: 3px;
  background: #66bb6a;
}
.gantt-actual-bar.late {
  background: #ef5350;
}
.gantt-actual-bar.early {
  background: #66bb6a;
}
.legend-swatch {
  display: inline-block;
  width: 14px;
  height: 6px;
  border-radius: 3px;
  margin-right: 4px;
}
.legend-baseline {
  background: repeating-linear-gradient(45deg, #b0bec5, #b0bec5 3px, #cfd8dc 3px, #cfd8dc 6px);
}
.legend-actual {
  background: #66bb6a;
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
