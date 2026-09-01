<template>
  <v-container fluid class="pa-6" style="max-width: 1100px">
    <div class="mb-6">
      <h1 class="text-h4 font-weight-bold">Bonjour {{ authStore.user?.first_name }} 👋</h1>
      <p class="text-medium-emphasis mb-0">Voici vos taches assignees, tous espaces de travail confondus.</p>
    </div>

    <div v-if="store.loading && !store.loaded" class="d-flex justify-center pa-12">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <template v-else>
      <v-row class="mb-4">
        <v-col v-for="stat in stats" :key="stat.key" cols="6" sm="3">
          <v-card
            :variant="activeFilter === stat.key ? 'flat' : 'tonal'"
            :color="activeFilter === stat.key ? stat.color : undefined"
            class="pa-4 stat-card"
            @click="toggleFilter(stat.key)"
          >
            <div class="text-caption" :class="activeFilter === stat.key ? 'text-white' : 'text-medium-emphasis'">{{ stat.label }}</div>
            <div class="text-h4 font-weight-bold" :class="activeFilter === stat.key ? 'text-white' : `text-${stat.color}`">
              {{ groups[stat.key].length }}
            </div>
          </v-card>
        </v-col>
      </v-row>

      <div v-if="!store.tasks.length" class="text-center pa-12 text-medium-emphasis">
        <v-icon icon="mdi-emoticon-happy-outline" size="48" class="mb-2" />
        <div>Aucune tache ne vous est assignee pour le moment.</div>
      </div>

      <template v-else>
        <div v-for="section in visibleSections" :key="section.key" class="mb-6">
          <div class="d-flex align-center mb-2">
            <v-icon :icon="section.icon" :color="section.color" size="18" class="mr-2" />
            <span class="text-subtitle-1 font-weight-bold">{{ section.label }}</span>
            <span class="text-caption text-medium-emphasis ml-2">({{ section.tasks.length }})</span>
          </div>
          <v-card variant="outlined">
            <v-list density="comfortable">
              <v-list-item v-for="t in section.tasks" :key="t.id" @click="openTask(t)">
                <template #prepend>
                  <v-progress-circular :model-value="t.progress" size="22" width="3" color="success" class="mr-3" />
                </template>
                <v-list-item-title>{{ t.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ t.project_name }} · {{ t.workspace_name }}</v-list-item-subtitle>
                <template #append>
                  <div class="d-flex align-center ga-2">
                    <v-chip size="x-small" :color="priorityColor(t.priority)" variant="tonal">{{ priorityLabel(t.priority) }}</v-chip>
                    <span v-if="t.due_date" class="text-caption text-medium-emphasis" style="min-width: 52px">{{ formatDue(t.due_date) }}</span>
                  </div>
                </template>
              </v-list-item>
            </v-list>
          </v-card>
        </div>

        <div v-if="groups.done.length">
          <v-btn variant="text" size="small" :prepend-icon="showDone ? 'mdi-chevron-down' : 'mdi-chevron-right'" @click="showDone = !showDone">
            Taches terminees ({{ groups.done.length }})
          </v-btn>
          <v-card v-if="showDone" variant="outlined" class="mt-2">
            <v-list density="comfortable">
              <v-list-item v-for="t in groups.done" :key="t.id" @click="openTask(t)">
                <template #prepend>
                  <v-progress-circular :model-value="t.progress" size="22" width="3" color="success" class="mr-3" />
                </template>
                <v-list-item-title>{{ t.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ t.project_name }} · {{ t.workspace_name }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card>
        </div>
      </template>
    </template>
  </v-container>
</template>

<script setup>
import { formatDate, parseDate } from "@/components/gantt/ganttMath";
import { useAuthStore } from "@/stores/auth";
import { useMyTasksStore } from "@/stores/myTasks";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const authStore = useAuthStore();
const store = useMyTasksStore();
const router = useRouter();
const activeFilter = ref(null);
const showDone = ref(false);

onMounted(() => store.fetchMine());

const stats = [
  { key: "overdue", label: "En retard", color: "error" },
  { key: "today", label: "Aujourd'hui", color: "warning" },
  { key: "upcoming", label: "A venir", color: "primary" },
  { key: "noDate", label: "Sans echeance", color: "grey" },
];

const sectionMeta = {
  overdue: { label: "En retard", icon: "mdi-alert-circle-outline", color: "error" },
  today: { label: "Aujourd'hui", icon: "mdi-calendar-today", color: "warning" },
  upcoming: { label: "A venir", icon: "mdi-calendar-arrow-right", color: "primary" },
  noDate: { label: "Sans echeance", icon: "mdi-calendar-blank-outline", color: "grey" },
};

function toggleFilter(key) {
  activeFilter.value = activeFilter.value === key ? null : key;
}

const groups = computed(() => {
  const today = formatDate(new Date());
  const buckets = { overdue: [], today: [], upcoming: [], noDate: [], done: [] };
  for (const t of store.tasks) {
    if (t.progress >= 100) {
      buckets.done.push(t);
    } else if (!t.due_date) {
      buckets.noDate.push(t);
    } else if (t.due_date < today) {
      buckets.overdue.push(t);
    } else if (t.due_date === today) {
      buckets.today.push(t);
    } else {
      buckets.upcoming.push(t);
    }
  }
  buckets.upcoming.sort((a, b) => a.due_date.localeCompare(b.due_date));
  return buckets;
});

const visibleSections = computed(() =>
  Object.keys(sectionMeta)
    .filter((key) => (!activeFilter.value || activeFilter.value === key) && groups.value[key].length)
    .map((key) => ({ key, ...sectionMeta[key], tasks: groups.value[key] }))
);

function openTask(task) {
  router.push({ name: "project", params: { id: task.project }, query: { openTask: task.id } });
}

const priorityLabels = { low: "Basse", medium: "Moyenne", high: "Haute", urgent: "Urgente" };
const priorityColors = { low: "grey", medium: "info", high: "warning", urgent: "error" };
function priorityLabel(p) {
  return priorityLabels[p] || p;
}
function priorityColor(p) {
  return priorityColors[p] || "grey";
}
function formatDue(iso) {
  return parseDate(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}
</script>

<style scoped>
.stat-card {
  cursor: pointer;
}
</style>
