<template>
  <div class="gantt-root d-flex flex-column fill-height">
    <div class="d-flex align-center px-4 py-2 gantt-toolbar">
      <v-btn-toggle v-model="zoom" density="compact" mandatory color="primary" variant="outlined">
        <v-btn value="day" size="small">Jour</v-btn>
        <v-btn value="week" size="small">Semaine</v-btn>
        <v-btn value="month" size="small">Mois</v-btn>
      </v-btn-toggle>
      <v-btn class="ml-3" size="small" variant="tonal" prepend-icon="mdi-calendar-today" @click="scrollToToday">Aujourd'hui</v-btn>
      <v-spacer />
      <span class="text-caption text-medium-emphasis">Glissez une barre pour replanifier, tirez ses extremites pour redimensionner</span>
    </div>
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
              <GanttBar
                v-if="row.bar"
                :task="row.task"
                :x="row.bar.x"
                :y="index * rowHeight"
                :width="row.bar.width"
                :row-height="rowHeight"
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
import { useTaskStore } from "@/stores/task";
import { computed, reactive, ref } from "vue";

const props = defineProps({ project: { type: Object, required: true } });
defineEmits(["open-task"]);

const taskStore = useTaskStore();
const zoom = ref("day");
const collapsed = reactive(new Set());
const bodyRef = ref(null);

const leftWidth = 280;
const rowHeight = 40;
const headerHeight = 52;
const dayWidth = computed(() => ZOOM_LEVELS[zoom.value].dayWidth);

const MONTH_LABEL = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" });
const DAY_LABEL = new Intl.DateTimeFormat("fr-FR", { day: "2-digit" });

const range = computed(() => {
  const dates = [];
  for (const t of taskStore.tasks) {
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
      out.push({ task, depth, hasChildren: children_, bar: computeBar(task) });
      if (children_ && !collapsed.has(task.id)) {
        walk(task.id, depth + 1);
      }
    }
  }
  walk(null, 0);
  return out;
});

function computeBar(task) {
  if (!task.start_date || !task.due_date) return null;
  const start = parseDate(task.start_date);
  const due = parseDate(task.due_date);
  const x = diffDays(range.value.start, start) * dayWidth.value;
  const width = Math.max(dayWidth.value, (diffDays(start, due) + 1) * dayWidth.value);
  return { x, width };
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
