<template>
  <div v-if="projectStore.current" class="d-flex flex-column fill-height">
    <div class="px-6 pt-6 pb-2">
      <div class="d-flex align-center">
        <v-avatar :color="projectStore.current.color" rounded="lg" class="mr-3">
          <v-icon :icon="projectStore.current.icon" color="white" />
        </v-avatar>
        <div>
          <h1 class="text-h5 font-weight-bold">{{ projectStore.current.name }}</h1>
          <p class="text-caption text-medium-emphasis mb-0">{{ projectStore.current.tasks_count }} tache(s) - {{ projectStore.current.progress }}% termine</p>
        </div>
        <v-spacer />
        <div class="d-flex mr-4">
          <v-avatar
            v-for="m in projectStore.current.members.slice(0, 5)"
            :key="m.id"
            :color="m.avatar_color"
            size="32"
            class="ml-n2 avatar-border"
          >
            <span class="text-caption text-white">{{ m.initials }}</span>
          </v-avatar>
        </div>
        <v-btn prepend-icon="mdi-account-multiple-outline" variant="tonal" class="mr-2" @click="membersDialog = true">Membres</v-btn>
        <v-btn v-if="isAdmin" color="primary" prepend-icon="mdi-plus" @click="openCreateTask()">Nouvelle tache</v-btn>
        <v-menu v-if="isAdmin">
          <template #activator="{ props: menuProps }">
            <v-btn v-bind="menuProps" icon="mdi-dots-vertical" variant="text" class="ml-1" />
          </template>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-view-column-outline" title="Colonnes et etiquettes" @click="columnsLabelsDialog = true" />
            <v-list-item prepend-icon="mdi-form-select" title="Champs personnalises" @click="customFieldsDialog = true" />
            <v-list-item prepend-icon="mdi-robot-outline" title="Automatisation" @click="automationDialog = true" />
            <v-list-item prepend-icon="mdi-content-save-outline" title="Enregistrer comme modele" @click="openSaveTemplate" />
            <v-list-item prepend-icon="mdi-content-copy" title="Dupliquer le projet" @click="duplicateProject" />
          </v-list>
        </v-menu>
      </div>
      <v-tabs v-model="tab" class="mt-4">
        <v-tab value="board" prepend-icon="mdi-view-column-outline">Tableau</v-tab>
        <v-tab value="gantt" prepend-icon="mdi-chart-gantt">Gantt</v-tab>
        <v-tab value="list" prepend-icon="mdi-format-list-bulleted">Liste</v-tab>
        <v-tab value="calendar" prepend-icon="mdi-calendar-month-outline">Calendrier</v-tab>
      </v-tabs>
    </div>
    <v-divider />
    <v-window v-model="tab" class="flex-grow-1 overflow-auto">
      <v-window-item value="board" class="pa-4">
        <KanbanBoard :project="projectStore.current" @open-task="openTask" @create-task="openCreateTask" />
      </v-window-item>
      <v-window-item value="gantt" class="fill-height">
        <GanttChart :project="projectStore.current" @open-task="openTask" />
      </v-window-item>
      <v-window-item value="list" class="pa-4">
        <TaskListView :project="projectStore.current" @open-task="openTask" />
      </v-window-item>
      <v-window-item value="calendar" class="pa-4">
        <CalendarView :project="projectStore.current" @open-task="openTask" />
      </v-window-item>
    </v-window>

    <TaskDetailDialog
      v-model="taskDialog"
      :task-id="selectedTaskId"
      :project="projectStore.current"
      :default-column="defaultColumn"
      @created="onTaskCreated"
      @open-task="openTask"
    />

    <CustomFieldsDialog v-model="customFieldsDialog" :project="projectStore.current" />
    <ColumnsLabelsDialog v-model="columnsLabelsDialog" :project="projectStore.current" />
    <AutomationRulesDialog v-model="automationDialog" :project="projectStore.current" />

    <v-dialog v-model="saveTemplateDialog" max-width="460">
      <v-card title="Enregistrer comme modele">
        <v-card-text>
          <p class="text-caption text-medium-emphasis mb-3">
            Le modele copie la structure (colonnes, etiquettes, champs personnalises) et le plan (taches,
            dependances) sans l'avancement ni les assignations. Le projet actuel n'est pas modifie.
          </p>
          <v-text-field v-model="templateName" label="Nom du modele" autofocus @keyup.enter="saveAsTemplate" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="saveTemplateDialog = false">Annuler</v-btn>
          <v-btn color="primary" :disabled="!templateName.trim()" @click="saveAsTemplate">Enregistrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="4000" color="success">{{ snackbarText }}</v-snackbar>

    <v-dialog v-model="membersDialog" max-width="520">
      <v-card title="Membres du projet">
        <v-card-subtitle class="px-4">
          Administrateur : cree/modifie le projet et ses taches. Membre : assigne a des taches, peut en changer le
          statut/avancement. Observateur : consultation seule.
        </v-card-subtitle>
        <v-card-text>
          <v-list>
            <v-list-item v-for="m in projectStore.members" :key="m.id" :title="m.user.first_name + ' ' + m.user.last_name">
              <template #prepend>
                <v-avatar :color="m.user.avatar_color">{{ m.user.initials }}</v-avatar>
              </template>
              <template #append>
                <template v-if="isAdmin">
                  <v-select
                    :model-value="m.role"
                    :items="roleOptions"
                    density="compact"
                    hide-details
                    variant="outlined"
                    style="max-width: 160px"
                    @update:model-value="(v) => changeRole(m, v)"
                  />
                  <v-btn icon="mdi-close" variant="text" size="small" class="ml-1" @click="removeMember(m)" />
                </template>
                <v-chip v-else size="small">{{ roleLabel(m.role) }}</v-chip>
              </template>
            </v-list-item>
          </v-list>
          <template v-if="isAdmin">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">Ajouter un membre</div>
            <v-select
              v-model="newMemberUserId"
              :items="addableWorkspaceMembers"
              item-title="label"
              item-value="id"
              label="Personne"
              density="compact"
            />
            <v-select v-model="newMemberRole" :items="roleOptions" label="Role" density="compact" />
            <v-btn color="primary" :disabled="!newMemberUserId" @click="addMember">Ajouter</v-btn>
          </template>
          <p v-else class="text-caption text-medium-emphasis mt-2">
            Seuls les administrateurs du projet peuvent gerer les membres.
          </p>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import CalendarView from "@/components/calendar/CalendarView.vue";
import GanttChart from "@/components/gantt/GanttChart.vue";
import KanbanBoard from "@/components/kanban/KanbanBoard.vue";
import AutomationRulesDialog from "@/components/project/AutomationRulesDialog.vue";
import ColumnsLabelsDialog from "@/components/project/ColumnsLabelsDialog.vue";
import CustomFieldsDialog from "@/components/project/CustomFieldsDialog.vue";
import TaskDetailDialog from "@/components/task/TaskDetailDialog.vue";
import TaskListView from "@/components/task/TaskListView.vue";
import { connectSocket } from "@/services/ws";
import { useDirectoryStore } from "@/stores/directory";
import { useNotificationStore } from "@/stores/notification";
import { useProjectStore } from "@/stores/project";
import { useTaskStore } from "@/stores/task";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const props = defineProps({ id: { type: [String, Number], required: true } });

const projectStore = useProjectStore();
const taskStore = useTaskStore();
const notificationStore = useNotificationStore();
const directoryStore = useDirectoryStore();
const route = useRoute();
const router = useRouter();

const tab = ref("board");
const taskDialog = ref(false);
const selectedTaskId = ref(null);
const defaultColumn = ref(null);
const membersDialog = ref(false);
const newMemberUserId = ref(null);
const newMemberRole = ref("member");
const customFieldsDialog = ref(false);
const columnsLabelsDialog = ref(false);
const automationDialog = ref(false);
const saveTemplateDialog = ref(false);
const templateName = ref("");
const snackbar = ref(false);
const snackbarText = ref("");
let socket = null;

const isAdmin = computed(() => projectStore.current?.my_role === "admin");

const roleOptions = [
  { title: "Administrateur", value: "admin" },
  { title: "Membre", value: "member" },
  { title: "Observateur", value: "viewer" },
];

function roleLabel(value) {
  return roleOptions.find((r) => r.value === value)?.title || value;
}

const addableWorkspaceMembers = computed(() => {
  // The whole company directory, not just people already in this workspace -
  // adding someone here folds them into the workspace automatically (backend).
  const existingUserIds = new Set(projectStore.members.map((m) => m.user.id));
  return directoryStore.users
    .filter((u) => !existingUserIds.has(u.id))
    .map((u) => ({ id: u.id, label: `${u.first_name} ${u.last_name} (${u.email})` }));
});

watch(membersDialog, async (open) => {
  if (open && projectStore.current) {
    newMemberUserId.value = null;
    newMemberRole.value = "member";
    await Promise.all([
      projectStore.fetchMembers(projectStore.current.id),
      directoryStore.fetchUsers(),
    ]);
  }
});

async function changeRole(membership, role) {
  await projectStore.addMember(projectStore.current.id, { user_id: membership.user.id, role });
}

async function removeMember(membership) {
  if (confirm(`Retirer ${membership.user.first_name} ${membership.user.last_name} du projet ?`)) {
    await projectStore.removeMember(projectStore.current.id, membership.user.id);
  }
}

async function addMember() {
  if (!newMemberUserId.value) return;
  await projectStore.addMember(projectStore.current.id, { user_id: newMemberUserId.value, role: newMemberRole.value });
  newMemberUserId.value = null;
  newMemberRole.value = "member";
}

async function load(id) {
  await projectStore.fetchProject(id);
  await taskStore.fetchTasks(id);
  socket?.close();
  socket = connectSocket(`projects/${id}`, (message) => {
    if (message.kind?.startsWith("task.")) {
      taskStore.applyRealtimeEvent(message.kind, message.payload);
    } else if (message.kind === "notification.created") {
      notificationStore.pushRealtime(message.payload);
    } else if (message.kind === "baseline.updated") {
      projectStore.fetchProject(id);
      taskStore.fetchTasks(id);
    }
  });

  if (route.query.openTask) {
    tab.value = "gantt";
    openTask(Number(route.query.openTask));
    router.replace({ query: { ...route.query, openTask: undefined } });
  }
}

onMounted(() => load(props.id));
watch(() => props.id, (id) => load(id));
onBeforeUnmount(() => socket?.close());

function openTask(id) {
  selectedTaskId.value = id;
  defaultColumn.value = null;
  taskDialog.value = true;
}

function openCreateTask(columnId = null) {
  selectedTaskId.value = null;
  defaultColumn.value = columnId;
  taskDialog.value = true;
}

function onTaskCreated(task) {
  selectedTaskId.value = task.id;
}

function openSaveTemplate() {
  templateName.value = `${projectStore.current.name} (modele)`;
  saveTemplateDialog.value = true;
}

async function saveAsTemplate() {
  const template = await projectStore.saveAsTemplate(projectStore.current.id, templateName.value.trim());
  saveTemplateDialog.value = false;
  snackbarText.value = `Modele "${template.name}" enregistre.`;
  snackbar.value = true;
}

async function duplicateProject() {
  const copy = await projectStore.duplicateProject(projectStore.current.id);
  router.push({ name: "project", params: { id: copy.id } });
}
</script>

<style scoped>
.avatar-border {
  border: 2px solid white;
}
</style>
