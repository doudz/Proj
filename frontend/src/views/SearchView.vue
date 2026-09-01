<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h4 font-weight-bold mb-1">Recherche avancee</h1>
    <p class="text-medium-emphasis">
      Filtrez toutes les taches de l'espace {{ workspaceStore.current?.name || "courant" }}, tous projets confondus.
      Le texte cherche aussi dans la description et les champs personnalises.
    </p>

    <v-card class="mb-4">
      <v-card-text>
        <v-row dense>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="filters.q"
              label="Texte"
              prepend-inner-icon="mdi-magnify"
              density="compact"
              clearable
              hide-details
              @keyup.enter="search"
            />
          </v-col>
          <v-col cols="12" sm="6" md="4">
            <v-select
              v-model="filters.projects"
              :items="projectStore.projects"
              item-title="name"
              item-value="id"
              label="Projets"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="12" sm="6" md="4">
            <v-select
              v-model="filters.assignees"
              :items="workspaceStore.members"
              :item-title="(m) => `${m.user.first_name} ${m.user.last_name}`"
              :item-value="(m) => m.user.id"
              label="Assignes"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="filters.state"
              :items="states"
              label="Etat"
              density="compact"
              clearable
              hide-details
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="filters.priorities"
              :items="priorities"
              label="Priorites"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-text-field v-model="filters.due_after" label="Echeance apres" type="date" density="compact" hide-details />
          </v-col>
          <v-col cols="6" md="2">
            <v-text-field v-model="filters.due_before" label="Echeance avant" type="date" density="compact" hide-details />
          </v-col>
          <v-col cols="12" md="2">
            <v-select v-model="filters.ordering" :items="orderings" label="Tri" density="compact" hide-details />
          </v-col>
        </v-row>
        <div class="d-flex align-center flex-wrap ga-4 mt-3">
          <v-checkbox v-model="filters.unassigned" label="Non assignees uniquement" density="compact" hide-details />
          <v-checkbox v-model="filters.milestones_only" label="Jalons uniquement" density="compact" hide-details />
          <v-spacer />
          <v-btn variant="text" @click="reset">Reinitialiser</v-btn>
          <v-btn variant="tonal" prepend-icon="mdi-content-save-outline" :disabled="!hasFilters" @click="openSave">
            Enregistrer
          </v-btn>
          <v-btn color="primary" prepend-icon="mdi-magnify" :loading="loading" @click="search">Rechercher</v-btn>
        </div>
      </v-card-text>
    </v-card>

    <div v-if="savedSearches.length" class="d-flex align-center flex-wrap ga-2 mb-4">
      <span class="text-caption text-medium-emphasis mr-1">Recherches enregistrees :</span>
      <v-chip
        v-for="saved in savedSearches"
        :key="saved.name"
        size="small"
        closable
        @click="applySaved(saved)"
        @click:close="removeSaved(saved)"
      >
        {{ saved.name }}
      </v-chip>
    </div>

    <v-card>
      <v-card-title class="text-subtitle-1">
        {{ results.length }} resultat(s)
        <span v-if="results.length >= 200" class="text-caption text-medium-emphasis">(limite a 200)</span>
      </v-card-title>
      <v-divider />
      <v-data-table
        :headers="headers"
        :items="results"
        :loading="loading"
        :items-per-page="25"
        density="comfortable"
        no-data-text="Aucune tache ne correspond a ces criteres."
        @click:row="(_, { item }) => openTask(item)"
      >
        <template #item.title="{ item }">
          <v-icon v-if="item.is_milestone" icon="mdi-flag-checkered" size="14" color="warning" class="mr-1" />
          <v-icon v-if="item.is_blocked" icon="mdi-lock-outline" size="14" color="warning" class="mr-1" />
          {{ item.title }}
        </template>
        <template #item.project_name="{ item }">
          <v-chip size="x-small" :color="item.project_color" label>{{ item.project_name }}</v-chip>
        </template>
        <template #item.priority="{ item }">
          <v-chip size="x-small" :color="priorityColor(item.priority)" variant="tonal">
            {{ priorityLabel(item.priority) }}
          </v-chip>
        </template>
        <template #item.due_date="{ item }">
          <span :class="{ 'text-error font-weight-medium': isLate(item) }">{{ item.due_date || "-" }}</span>
        </template>
        <template #item.assignees="{ item }">
          <div class="d-flex ml-n1">
            <v-avatar
              v-for="a in item.assignees"
              :key="a.id"
              :color="a.avatar_color"
              size="24"
              class="ml-n1"
              :title="`${a.first_name} ${a.last_name}`"
            >
              <span class="text-caption text-white">{{ a.initials }}</span>
            </v-avatar>
            <span v-if="!item.assignees.length && !item.external_assignees.length" class="text-medium-emphasis">-</span>
          </div>
        </template>
        <template #item.progress="{ item }">
          <v-progress-linear :model-value="item.progress" height="6" rounded color="success" style="width: 90px" />
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="saveDialog" max-width="420">
      <v-card title="Enregistrer cette recherche">
        <v-card-text>
          <v-text-field v-model="saveName" label="Nom" autofocus @keyup.enter="saveSearch" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="saveDialog = false">Annuler</v-btn>
          <v-btn color="primary" :disabled="!saveName.trim()" @click="saveSearch">Enregistrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import api from "@/services/api";
import { useProjectStore } from "@/stores/project";
import { useWorkspaceStore } from "@/stores/workspace";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";

const STORAGE_KEY = "ganttflow_saved_searches";

const workspaceStore = useWorkspaceStore();
const projectStore = useProjectStore();
const router = useRouter();

const loading = ref(false);
const results = ref([]);
const saveDialog = ref(false);
const saveName = ref("");
const savedSearches = ref([]);

const emptyFilters = {
  q: "",
  projects: [],
  assignees: [],
  priorities: [],
  state: null,
  due_after: "",
  due_before: "",
  unassigned: false,
  milestones_only: false,
  ordering: "due_date",
};
const filters = reactive({ ...emptyFilters });

const states = [
  { title: "Ouvertes", value: "open" },
  { title: "En retard", value: "late" },
  { title: "En cours", value: "in_progress" },
  { title: "Non demarrees", value: "not_started" },
  { title: "Terminees", value: "done" },
  { title: "Non planifiees", value: "unscheduled" },
  { title: "Bloquees", value: "blocked" },
];

const priorities = [
  { title: "Basse", value: "low" },
  { title: "Moyenne", value: "medium" },
  { title: "Haute", value: "high" },
  { title: "Urgente", value: "urgent" },
];

const orderings = [
  { title: "Echeance croissante", value: "due_date" },
  { title: "Echeance decroissante", value: "-due_date" },
  { title: "Debut croissant", value: "start_date" },
  { title: "Titre", value: "title" },
  { title: "Avancement", value: "-progress" },
  { title: "Creation recente", value: "-created_at" },
];

const headers = [
  { title: "Tache", key: "title" },
  { title: "Projet", key: "project_name" },
  { title: "Priorite", key: "priority" },
  { title: "Debut", key: "start_date" },
  { title: "Echeance", key: "due_date" },
  { title: "Duree", key: "duration_days" },
  { title: "Assignes", key: "assignees", sortable: false },
  { title: "Avancement", key: "progress" },
];

const priorityLabels = { low: "Basse", medium: "Moyenne", high: "Haute", urgent: "Urgente" };
const priorityColors = { low: "grey", medium: "info", high: "warning", urgent: "error" };

const hasFilters = computed(() =>
  Object.entries(filters).some(([key, value]) => {
    if (key === "ordering") return false;
    return Array.isArray(value) ? value.length > 0 : Boolean(value);
  })
);

function priorityLabel(value) {
  return priorityLabels[value] || value;
}

function priorityColor(value) {
  return priorityColors[value] || "grey";
}

function isLate(task) {
  return task.due_date && task.progress < 100 && task.due_date < new Date().toISOString().slice(0, 10);
}

function buildParams() {
  const params = { ordering: filters.ordering };
  if (workspaceStore.current) params.workspace = workspaceStore.current.id;
  if (filters.q) params.q = filters.q;
  if (filters.projects.length) params.projects = filters.projects.join(",");
  if (filters.assignees.length) params.assignees = filters.assignees.join(",");
  if (filters.priorities.length) params.priorities = filters.priorities.join(",");
  if (filters.state) params.state = filters.state;
  if (filters.due_after) params.due_after = filters.due_after;
  if (filters.due_before) params.due_before = filters.due_before;
  if (filters.unassigned) params.unassigned = "true";
  if (filters.milestones_only) params.milestones_only = "true";
  return params;
}

async function search() {
  loading.value = true;
  try {
    const { data } = await api.get("/tasks/search/", { params: buildParams() });
    results.value = data;
  } finally {
    loading.value = false;
  }
}

function reset() {
  Object.assign(filters, { ...emptyFilters, projects: [], assignees: [], priorities: [] });
  search();
}

function openTask(task) {
  router.push({ name: "project", params: { id: task.project }, query: { openTask: task.id } });
}

function loadSaved() {
  try {
    savedSearches.value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    savedSearches.value = [];
  }
}

function persistSaved() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(savedSearches.value));
}

function openSave() {
  saveName.value = "";
  saveDialog.value = true;
}

function saveSearch() {
  const name = saveName.value.trim();
  if (!name) return;
  savedSearches.value = [...savedSearches.value.filter((s) => s.name !== name), { name, filters: { ...filters } }];
  persistSaved();
  saveDialog.value = false;
}

function applySaved(saved) {
  Object.assign(filters, { ...emptyFilters, ...saved.filters });
  search();
}

function removeSaved(saved) {
  savedSearches.value = savedSearches.value.filter((s) => s.name !== saved.name);
  persistSaved();
}

onMounted(async () => {
  loadSaved();
  if (workspaceStore.current) await workspaceStore.fetchMembers(workspaceStore.current.id);
  await search();
});

watch(
  () => workspaceStore.current,
  async (ws) => {
    if (ws) await workspaceStore.fetchMembers(ws.id);
    await search();
  }
);
</script>
