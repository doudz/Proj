<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center mb-5">
      <div>
        <h1 class="text-h4 font-weight-bold">Tableau de bord</h1>
        <p class="text-medium-emphasis mb-0">
          {{ workspaceStore.current?.name || "Tous les espaces" }} - {{ data?.totals?.projects || 0 }} projet(s)
        </p>
      </div>
      <v-spacer />
      <v-select
        v-model="projectFilter"
        :items="projectItems"
        item-title="name"
        item-value="id"
        label="Filtrer sur un projet"
        density="compact"
        hide-details
        clearable
        style="max-width: 260px"
      />
      <v-btn icon="mdi-refresh" variant="text" class="ml-2" :loading="loading" @click="load" />
    </div>

    <v-progress-linear v-if="loading && !data" indeterminate color="primary" class="mb-4" />

    <template v-if="data">
      <v-row dense class="mb-2">
        <v-col v-for="tile in tiles" :key="tile.label" cols="6" sm="4" md="2">
          <v-card variant="tonal" :color="tile.color" class="h-100">
            <v-card-text class="py-3">
              <div class="d-flex align-center">
                <v-icon :icon="tile.icon" size="20" class="mr-2" />
                <span class="text-caption">{{ tile.label }}</span>
              </div>
              <div class="text-h4 font-weight-bold mt-1">{{ tile.value }}</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1">Repartition par statut</v-card-title>
            <v-card-text>
              <div v-for="row in data.by_status" :key="row.name" class="mb-3">
                <div class="d-flex align-center text-caption mb-1">
                  <span class="dot mr-2" :style="{ backgroundColor: row.color }"></span>
                  <span>{{ row.name }}</span>
                  <v-spacer />
                  <strong>{{ row.count }}</strong>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: pct(row.count, maxStatus) + '%', backgroundColor: row.color }"></div>
                </div>
              </div>
              <p v-if="!data.by_status.length" class="text-medium-emphasis">Aucune tache.</p>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1">Par priorite</v-card-title>
            <v-card-text class="d-flex align-center">
              <svg :viewBox="`0 0 ${donutSize} ${donutSize}`" class="donut">
                <circle
                  :cx="donutSize / 2"
                  :cy="donutSize / 2"
                  :r="donutRadius"
                  fill="none"
                  stroke="rgba(0,0,0,0.06)"
                  :stroke-width="donutWidth"
                />
                <circle
                  v-for="arc in priorityArcs"
                  :key="arc.priority"
                  :cx="donutSize / 2"
                  :cy="donutSize / 2"
                  :r="donutRadius"
                  fill="none"
                  :stroke="arc.color"
                  :stroke-width="donutWidth"
                  :stroke-dasharray="`${arc.length} ${donutCircumference}`"
                  :stroke-dashoffset="-arc.offset"
                  :transform="`rotate(-90 ${donutSize / 2} ${donutSize / 2})`"
                />
                <text :x="donutSize / 2" :y="donutSize / 2 - 2" text-anchor="middle" class="donut-value">
                  {{ data.totals.total }}
                </text>
                <text :x="donutSize / 2" :y="donutSize / 2 + 16" text-anchor="middle" class="donut-label">taches</text>
              </svg>
              <div class="ml-6 flex-grow-1">
                <div v-for="row in data.by_priority" :key="row.priority" class="d-flex align-center text-caption mb-2">
                  <span class="dot mr-2" :style="{ backgroundColor: row.color }"></span>
                  <span>{{ row.label }}</span>
                  <v-spacer />
                  <strong>{{ row.count }}</strong>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1">Charge par personne</v-card-title>
            <v-card-subtitle class="text-caption">Taches ouvertes, dont en retard</v-card-subtitle>
            <v-card-text>
              <div v-for="row in data.by_assignee" :key="row.name" class="mb-3">
                <div class="d-flex align-center text-caption mb-1">
                  <v-avatar :color="row.color" size="22" class="mr-2">
                    <span class="text-white" style="font-size: 10px">{{ initials(row.name) }}</span>
                  </v-avatar>
                  <span>{{ row.name }}</span>
                  <v-spacer />
                  <strong>{{ row.open }}</strong>
                  <span v-if="row.late" class="text-error ml-2">({{ row.late }} en retard)</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: pct(row.open, maxWorkload) + '%', backgroundColor: row.color }"></div>
                  <div
                    v-if="row.late"
                    class="bar-fill bar-late"
                    :style="{ width: pct(row.late, maxWorkload) + '%' }"
                  ></div>
                </div>
              </div>
              <p v-if="!data.by_assignee.length" class="text-medium-emphasis">Aucune tache.</p>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1">Avancement par projet</v-card-title>
            <v-card-text>
              <div v-for="row in data.by_project" :key="row.id" class="mb-3">
                <div class="d-flex align-center text-caption mb-1">
                  <v-icon :icon="row.icon" size="16" :color="row.color" class="mr-2" />
                  <router-link :to="{ name: 'project', params: { id: row.id } }" class="project-link">
                    {{ row.name }}
                  </router-link>
                  <v-spacer />
                  <span>{{ row.done }}/{{ row.total }}</span>
                  <span v-if="row.late" class="text-error ml-2">{{ row.late }} en retard</span>
                </div>
                <v-progress-linear :model-value="row.progress" height="8" rounded :color="row.color" />
              </div>
              <p v-if="!data.by_project.length" class="text-medium-emphasis">Aucun projet.</p>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card>
            <v-card-title class="text-subtitle-1">Activite des 30 derniers jours</v-card-title>
            <v-card-subtitle class="text-caption">
              <span class="legend-swatch legend-done"></span>Terminees
              <span class="legend-swatch legend-created ml-3"></span>Creees
            </v-card-subtitle>
            <v-card-text>
              <svg viewBox="0 0 640 170" class="trend" preserveAspectRatio="none">
                <line v-for="y in [0, 40, 80, 120]" :key="y" x1="0" :y1="y + 10" x2="640" :y2="y + 10" class="grid-line" />
                <polyline :points="trendPoints.created" class="trend-line trend-created" />
                <polyline :points="trendPoints.completed" class="trend-line trend-completed" />
              </svg>
              <div class="d-flex justify-space-between text-caption text-medium-emphasis mt-1">
                <span>{{ formatDay(data.trend[0]?.date) }}</span>
                <span>{{ formatDay(data.trend[data.trend.length - 1]?.date) }}</span>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1 text-error">En retard ({{ data.overdue.length }})</v-card-title>
            <v-card-text class="pa-0">
              <v-list v-if="data.overdue.length" density="compact">
                <v-list-item v-for="task in data.overdue" :key="task.id" :to="taskLink(task)">
                  <v-list-item-title>{{ task.title }}</v-list-item-title>
                  <v-list-item-subtitle>{{ task.project_name }} - echeance {{ task.due_date }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
              <p v-else class="text-medium-emphasis pa-4 mb-0">Rien en retard, bravo.</p>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1">A venir (7 jours)</v-card-title>
            <v-card-text class="pa-0">
              <v-list v-if="data.upcoming.length" density="compact">
                <v-list-item v-for="task in data.upcoming" :key="task.id" :to="taskLink(task)">
                  <v-list-item-title>{{ task.title }}</v-list-item-title>
                  <v-list-item-subtitle>{{ task.project_name }} - echeance {{ task.due_date }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
              <p v-else class="text-medium-emphasis pa-4 mb-0">Aucune echeance dans les 7 prochains jours.</p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </v-container>
</template>

<script setup>
import api from "@/services/api";
import { useProjectStore } from "@/stores/project";
import { useWorkspaceStore } from "@/stores/workspace";
import { computed, onMounted, ref, watch } from "vue";

const workspaceStore = useWorkspaceStore();
const projectStore = useProjectStore();

const data = ref(null);
const loading = ref(false);
const projectFilter = ref(null);

const donutSize = 150;
const donutWidth = 22;
const donutRadius = (donutSize - donutWidth) / 2;
const donutCircumference = 2 * Math.PI * donutRadius;

const projectItems = computed(() => projectStore.projects);

const tiles = computed(() => {
  const t = data.value?.totals || {};
  return [
    { label: "Taches", value: t.total || 0, icon: "mdi-format-list-checks", color: "primary" },
    { label: "Terminees", value: t.done || 0, icon: "mdi-check-circle-outline", color: "success" },
    { label: "En retard", value: t.late || 0, icon: "mdi-alert-circle-outline", color: "error" },
    { label: "En cours", value: t.in_progress || 0, icon: "mdi-progress-clock", color: "info" },
    { label: "Non planifiees", value: t.unscheduled || 0, icon: "mdi-calendar-question-outline", color: "warning" },
    { label: "Jalons", value: t.milestones || 0, icon: "mdi-flag-checkered", color: "purple" },
  ];
});

const maxStatus = computed(() => Math.max(1, ...(data.value?.by_status || []).map((r) => r.count)));
const maxWorkload = computed(() => Math.max(1, ...(data.value?.by_assignee || []).map((r) => r.total)));

const priorityArcs = computed(() => {
  const rows = data.value?.by_priority || [];
  const total = rows.reduce((sum, r) => sum + r.count, 0) || 1;
  let offset = 0;
  return rows.map((row) => {
    const length = (row.count / total) * donutCircumference;
    const arc = { priority: row.priority, color: row.color, length, offset };
    offset += length;
    return arc;
  });
});

const trendPoints = computed(() => {
  const rows = data.value?.trend || [];
  if (!rows.length) return { completed: "", created: "" };
  const max = Math.max(1, ...rows.map((r) => Math.max(r.completed, r.created)));
  const stepX = 640 / Math.max(1, rows.length - 1);
  const toLine = (key) =>
    rows.map((row, i) => `${(i * stepX).toFixed(1)},${(140 - (row[key] / max) * 120 + 10).toFixed(1)}`).join(" ");
  return { completed: toLine("completed"), created: toLine("created") };
});

function pct(value, max) {
  return Math.round((value / max) * 100);
}

function initials(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

function formatDay(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}

function taskLink(task) {
  return { name: "project", params: { id: task.project }, query: { openTask: task.id } };
}

async function load() {
  loading.value = true;
  try {
    const params = {};
    if (workspaceStore.current) params.workspace = workspaceStore.current.id;
    if (projectFilter.value) params.project = projectFilter.value;
    const response = await api.get("/dashboard/", { params });
    data.value = response.data;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(() => workspaceStore.current, () => {
  // The project filter belongs to the workspace we are leaving.
  if (projectFilter.value) projectFilter.value = null;
  else load();
});
watch(projectFilter, load);
</script>

<style scoped>
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.bar-track {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
.bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 4px;
}
.bar-late {
  background: #ef5350;
}
.donut {
  width: 150px;
  height: 150px;
  flex: none;
}
.donut-value {
  font-size: 26px;
  font-weight: 700;
  fill: rgba(0, 0, 0, 0.82);
}
.donut-label {
  font-size: 11px;
  fill: rgba(0, 0, 0, 0.55);
}
.trend {
  width: 100%;
  height: 170px;
}
.grid-line {
  stroke: rgba(0, 0, 0, 0.06);
  stroke-width: 1;
}
.trend-line {
  fill: none;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}
.trend-completed {
  stroke: #66bb6a;
}
.trend-created {
  stroke: #42a5f5;
  stroke-dasharray: 4 3;
}
.legend-swatch {
  display: inline-block;
  width: 12px;
  height: 4px;
  border-radius: 2px;
  margin-right: 4px;
  vertical-align: middle;
}
.legend-done {
  background: #66bb6a;
}
.legend-created {
  background: #42a5f5;
}
.project-link {
  color: inherit;
  text-decoration: none;
}
.project-link:hover {
  text-decoration: underline;
}
</style>
