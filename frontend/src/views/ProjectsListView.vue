<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4 font-weight-bold">Projets</h1>
      <v-spacer />
      <v-select
        v-model="statusFilter"
        :items="statuses"
        label="Statut"
        style="max-width: 220px"
        clearable
        hide-details
        density="compact"
        class="mr-4"
      />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="dialog = true">Nouveau projet</v-btn>
    </div>

    <v-table>
      <thead>
        <tr>
          <th>Projet</th>
          <th>Statut</th>
          <th>Debut</th>
          <th>Echeance</th>
          <th>Avancement</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in filtered" :key="p.id" class="cursor-pointer" @click="$router.push({ name: 'project', params: { id: p.id } })">
          <td>
            <div class="d-flex align-center py-2">
              <v-avatar :color="p.color" size="28" class="mr-2" rounded="lg"><v-icon :icon="p.icon" size="16" color="white" /></v-avatar>
              {{ p.name }}
            </div>
          </td>
          <td><v-chip size="small" :color="statusColor(p.status)">{{ statusLabel(p.status) }}</v-chip></td>
          <td>{{ p.start_date || "-" }}</td>
          <td>{{ p.end_date || "-" }}</td>
          <td style="width: 160px">
            <v-progress-linear :model-value="p.progress" height="6" rounded color="success" />
          </td>
          <td>
            <v-btn icon="mdi-delete-outline" variant="text" size="small" @click.stop="remove(p.id)" />
          </td>
        </tr>
      </tbody>
    </v-table>

    <v-dialog v-model="dialog" max-width="420">
      <v-card title="Nouveau projet">
        <v-card-text>
          <v-text-field v-model="name" label="Nom du projet" autofocus @keyup.enter="create" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Annuler</v-btn>
          <v-btn color="primary" @click="create">Creer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { useProjectStore } from "@/stores/project";
import { useWorkspaceStore } from "@/stores/workspace";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const projectStore = useProjectStore();
const workspaceStore = useWorkspaceStore();
const router = useRouter();

const dialog = ref(false);
const name = ref("");
const statusFilter = ref(null);
const statuses = [
  { title: "Planifie", value: "planned" },
  { title: "En cours", value: "active" },
  { title: "En pause", value: "on_hold" },
  { title: "Termine", value: "done" },
  { title: "Archive", value: "archived" },
];

const filtered = computed(() =>
  statusFilter.value ? projectStore.projects.filter((p) => p.status === statusFilter.value) : projectStore.projects
);

onMounted(() => {
  if (workspaceStore.current) projectStore.fetchProjects(workspaceStore.current.id);
});

function statusLabel(status) {
  return statuses.find((s) => s.value === status)?.title || status;
}
function statusColor(status) {
  return { planned: "grey", active: "primary", on_hold: "warning", done: "success", archived: "grey-darken-1" }[status];
}

async function create() {
  if (!name.value.trim()) return;
  const project = await projectStore.createProject({ name: name.value, workspace: workspaceStore.current.id });
  name.value = "";
  dialog.value = false;
  router.push({ name: "project", params: { id: project.id } });
}

async function remove(id) {
  if (confirm("Supprimer ce projet ?")) await projectStore.deleteProject(id);
}
</script>
