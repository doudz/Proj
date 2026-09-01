<template>
  <v-dialog :model-value="modelValue" max-width="960" scrollable @update:model-value="close">
    <v-card v-if="isCreate">
      <v-card-title>Nouvelle tache</v-card-title>
      <v-card-text>
        <v-text-field v-model="createForm.title" label="Titre" autofocus @keyup.enter="create" />
        <v-row>
          <v-col cols="6"><v-text-field v-model="createForm.start_date" label="Debut" type="date" /></v-col>
          <v-col cols="6"><v-text-field v-model="createForm.due_date" label="Echeance" type="date" /></v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Annuler</v-btn>
        <v-btn color="primary" :disabled="!createForm.title.trim()" @click="create">Creer</v-btn>
      </v-card-actions>
    </v-card>

    <v-card v-else-if="task">
      <v-card-title class="d-flex align-center">
        <v-text-field
          v-model="task.title"
          variant="plain"
          density="compact"
          hide-details
          class="text-h6"
          @blur="patch({ title: task.title })"
        />
        <v-btn icon="mdi-close" variant="text" @click="close" />
      </v-card-title>
      <v-divider />
      <v-row no-gutters style="min-height: 520px">
        <v-col cols="7" class="pa-4 overflow-y-auto" style="max-height: 70vh">
          <v-textarea
            v-model="task.description"
            label="Description"
            variant="outlined"
            rows="3"
            @blur="patch({ description: task.description })"
          />
          <v-row>
            <v-col cols="6">
              <v-select
                v-model="task.column"
                :items="project.columns"
                item-title="name"
                item-value="id"
                label="Statut"
                @update:model-value="(v) => patch({ column: v })"
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="task.priority"
                :items="priorities"
                label="Priorite"
                @update:model-value="(v) => patch({ priority: v })"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field v-model="task.start_date" label="Debut" type="date" @change="patch({ start_date: task.start_date })" />
            </v-col>
            <v-col cols="6">
              <v-text-field v-model="task.due_date" label="Echeance" type="date" @change="patch({ due_date: task.due_date })" />
            </v-col>
            <v-col cols="12">
              <v-select
                v-model="task.assignees"
                :items="project.members"
                item-title="first_name"
                item-value="id"
                label="Assignes"
                multiple
                chips
                return-object
                @update:model-value="onAssigneesChange"
              />
            </v-col>
            <v-col cols="12">
              <div class="d-flex align-center ga-2">
                <v-select
                  v-model="task.external_assignees"
                  :items="workspaceStore.externalContacts"
                  item-title="name"
                  item-value="id"
                  label="Assignes externes (sous-traitants)"
                  multiple
                  chips
                  return-object
                  hide-details
                  @update:model-value="onExternalAssigneesChange"
                >
                  <template #chip="{ item, props: chipProps }">
                    <v-chip v-bind="chipProps" prepend-icon="mdi-account-hard-hat-outline">{{ item.raw.name }}</v-chip>
                  </template>
                </v-select>
                <v-btn icon="mdi-plus" size="small" variant="tonal" title="Nouveau contact externe" @click="quickContactDialog = true" />
              </div>
              <p class="text-caption text-medium-emphasis mt-1">
                Personnes/sous-traitants sans compte GanttFlow : notifies par e-mail uniquement (assignation, tache
                disponible).
              </p>
            </v-col>
            <v-col cols="12">
              <v-select
                v-model="task.labels"
                :items="project.labels"
                item-title="name"
                item-value="id"
                label="Etiquettes"
                multiple
                chips
                return-object
                @update:model-value="onLabelsChange"
              />
            </v-col>
            <v-col cols="12">
              <div class="d-flex align-center mb-1">
                <span class="text-caption">Avancement</span>
                <v-spacer />
                <span class="text-caption">{{ task.progress }}%</span>
              </div>
              <v-slider v-model="task.progress" :max="100" step="5" @end="patch({ progress: task.progress })" />
            </v-col>
            <v-col cols="12">
              <v-checkbox v-model="task.is_milestone" label="Marquer comme jalon (milestone)" @change="patch({ is_milestone: task.is_milestone })" />
            </v-col>
          </v-row>

          <v-divider class="my-2" />
          <div class="d-flex align-center mb-2">
            <span class="text-subtitle-2">Suivi reel</span>
            <v-spacer />
            <v-tooltip :disabled="!task.is_blocked" location="top">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps">
                  <v-btn size="x-small" variant="tonal" class="mr-1" :disabled="task.is_blocked" @click="startNow">
                    Demarrer aujourd'hui
                  </v-btn>
                </span>
              </template>
              <span>Bloquee par : {{ task.blocking_predecessor_titles.join(", ") }}</span>
            </v-tooltip>
            <v-btn size="x-small" variant="tonal" color="success" @click="completeNow">Terminer aujourd'hui</v-btn>
          </div>
          <p class="text-caption text-medium-emphasis mb-2">
            Les dates reelles sont libres : une tache peut demarrer ou se terminer avant ou apres les dates planifiees ci-dessus.
          </p>
          <v-alert v-if="task.is_blocked" density="compact" variant="tonal" color="warning" class="mb-2">
            <v-icon icon="mdi-lock-outline" size="16" class="mr-1" />
            En attente de : {{ task.blocking_predecessor_titles.join(", ") }}
          </v-alert>
          <v-alert v-if="startError" density="compact" variant="tonal" color="error" class="mb-2" closable @click:close="startError = ''">
            {{ startError }}
          </v-alert>
          <v-row>
            <v-col cols="6">
              <v-text-field
                v-model="task.actual_start_date"
                label="Debut reel"
                type="date"
                @change="patch({ actual_start_date: task.actual_start_date || null })"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="task.actual_end_date"
                label="Fin reelle"
                type="date"
                @change="patch({ actual_end_date: task.actual_end_date || null })"
              />
            </v-col>
          </v-row>
          <v-alert v-if="task.baseline_start_date" density="compact" variant="tonal" color="blue-grey" class="mb-2">
            <div class="text-caption">
              Ligne de base : {{ task.baseline_start_date }} &rarr; {{ task.baseline_end_date }}
            </div>
            <div v-if="varianceLabel" class="text-caption font-weight-medium">{{ varianceLabel }}</div>
          </v-alert>

          <v-divider class="my-2" />
          <div class="d-flex align-center mb-2">
            <span class="text-subtitle-2">Sous-taches ({{ subtasks.length }})</span>
          </div>
          <v-list density="compact">
            <v-list-item v-for="s in subtasks" :key="s.id" @click="$emit('open-task', s.id)">
              <template #prepend>
                <v-progress-circular :model-value="s.progress" size="20" width="3" color="success" />
              </template>
              <v-list-item-title>{{ s.title }}</v-list-item-title>
            </v-list-item>
          </v-list>
          <v-text-field
            v-model="newSubtask"
            placeholder="Ajouter une sous-tache et appuyer sur Entree"
            density="compact"
            hide-details
            variant="outlined"
            class="mt-1"
            @keyup.enter="addSubtask"
          />

          <v-divider class="my-2" />
          <div class="text-subtitle-2 mb-1">Dependances (a demarrer apres)</div>
          <p class="text-caption text-medium-emphasis mb-2">
            Cliquez sur le cadenas d'une dependance pour la rendre bloquante : la tache ne pourra alors pas etre
            demarree tant que la precedente n'est pas terminee, et ses assignes seront notifies (in-app + e-mail)
            des qu'elle redevient disponible.
          </p>
          <v-chip
            v-for="dep in predecessorDeps"
            :key="dep.id"
            closable
            size="small"
            class="mr-1 mb-1"
            :color="dep.enforce_blocking ? 'warning' : undefined"
            @click:close="removeDependency(dep.id)"
          >
            <v-icon
              :icon="dep.enforce_blocking ? 'mdi-lock' : 'mdi-lock-open-variant-outline'"
              size="16"
              class="mr-1"
              @click.stop="toggleBlocking(dep)"
            />
            {{ taskTitle(dep.predecessor) }}
          </v-chip>
          <v-row class="align-center" no-gutters>
            <v-col cols="8">
              <v-autocomplete
                v-model="pendingDependency"
                :items="dependencyCandidates"
                item-title="title"
                item-value="id"
                label="Ajouter une dependance"
                density="compact"
                hide-details
                variant="outlined"
              />
            </v-col>
            <v-col cols="4" class="d-flex align-center pl-2">
              <v-checkbox v-model="pendingBlocking" label="Bloquante" density="compact" hide-details />
            </v-col>
          </v-row>
          <v-btn
            size="small"
            variant="tonal"
            class="mt-2"
            :disabled="!pendingDependency"
            @click="addDependency"
          >
            Ajouter
          </v-btn>
        </v-col>
        <v-col cols="5" class="border-s" style="max-height: 70vh">
          <TaskComments :task-id="task.id" />
        </v-col>
      </v-row>
      <v-divider />
      <v-card-actions>
        <v-btn color="error" variant="text" prepend-icon="mdi-delete-outline" @click="remove">Supprimer</v-btn>
        <v-spacer />
        <span class="text-caption text-medium-emphasis">Modifie le {{ formatDate(task.updated_at) }}</span>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="quickContactDialog" max-width="420">
    <v-card title="Nouveau contact externe">
      <v-card-text>
        <p class="text-caption text-medium-emphasis mb-3">
          Pour une personne ou un sous-traitant sans compte GanttFlow (travail externalise). Il/elle sera notifie(e)
          par e-mail lors de l'assignation.
        </p>
        <v-text-field v-model="quickContact.name" label="Nom" autofocus />
        <v-text-field v-model="quickContact.email" label="E-mail (pour les notifications)" />
        <v-text-field v-model="quickContact.company" label="Societe (optionnel)" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="quickContactDialog = false">Annuler</v-btn>
        <v-btn color="primary" :disabled="!quickContact.name.trim()" @click="createQuickContact">Ajouter et assigner</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import TaskComments from "@/components/task/TaskComments.vue";
import { useTaskStore } from "@/stores/task";
import { useWorkspaceStore } from "@/stores/workspace";
import { computed, reactive, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  taskId: { type: [String, Number], default: null },
  project: { type: Object, required: true },
  defaultColumn: { type: [String, Number], default: null },
});
const emit = defineEmits(["update:modelValue", "open-task", "created"]);

const taskStore = useTaskStore();
const workspaceStore = useWorkspaceStore();
const isCreate = computed(() => props.modelValue && !props.taskId);
const task = computed(() => (props.taskId ? taskStore.byId(Number(props.taskId)) : null));
const newSubtask = ref("");
const pendingDependency = ref(null);
const pendingBlocking = ref(false);
const startError = ref("");
const quickContactDialog = ref(false);
const quickContact = reactive({ name: "", email: "", company: "" });

const priorities = [
  { title: "Basse", value: "low" },
  { title: "Moyenne", value: "medium" },
  { title: "Haute", value: "high" },
  { title: "Urgente", value: "urgent" },
];

const createForm = reactive({ title: "", start_date: "", due_date: "" });

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      createForm.title = "";
      createForm.start_date = "";
      createForm.due_date = "";
      pendingDependency.value = null;
      pendingBlocking.value = false;
      startError.value = "";
      quickContactDialog.value = false;
    }
  }
);

const subtasks = computed(() => (task.value ? taskStore.subtasksOf(task.value.id) : []));

const predecessorDeps = computed(() =>
  task.value ? taskStore.dependencies.filter((d) => d.successor === task.value.id) : []
);

const dependencyCandidates = computed(() => {
  if (!task.value) return [];
  const existing = new Set(predecessorDeps.value.map((d) => d.predecessor));
  return taskStore.tasks.filter((t) => t.id !== task.value.id && !existing.has(t.id));
});

function taskTitle(id) {
  return taskStore.byId(id)?.title || "?";
}

function close() {
  emit("update:modelValue", false);
}

async function create() {
  const task_ = await taskStore.createTask({
    project: props.project.id,
    column: props.defaultColumn || props.project.columns[0]?.id,
    title: createForm.title,
    start_date: createForm.start_date || null,
    due_date: createForm.due_date || null,
  });
  emit("created", task_);
}

async function patch(payload) {
  if (task.value) await taskStore.updateTask(task.value.id, payload);
}

async function startNow() {
  if (!task.value) return;
  startError.value = "";
  try {
    await taskStore.startTask(task.value.id);
  } catch (e) {
    startError.value = e.response?.data?.detail || "Impossible de demarrer cette tache.";
  }
}

async function completeNow() {
  if (task.value) await taskStore.completeTask(task.value.id);
}

const varianceLabel = computed(() => {
  if (!task.value) return "";
  const variance = task.value.end_variance_days;
  if (variance === null || variance === undefined) return "";
  if (variance > 0) return `Retard de ${variance} jour(s) par rapport a la ligne de base`;
  if (variance < 0) return `Avance de ${-variance} jour(s) par rapport a la ligne de base`;
  return "Termine a la date prevue par la ligne de base";
});

function onAssigneesChange(values) {
  const ids = values.map((v) => (typeof v === "object" ? v.id : v));
  patch({ assignee_ids: ids });
}

function onExternalAssigneesChange(values) {
  const ids = values.map((v) => (typeof v === "object" ? v.id : v));
  patch({ external_assignee_ids: ids });
}

async function createQuickContact() {
  if (!quickContact.name.trim() || !task.value) return;
  const contact = await workspaceStore.createExternalContact({
    name: quickContact.name,
    email: quickContact.email,
    company: quickContact.company,
    workspace: props.project.workspace,
  });
  quickContact.name = "";
  quickContact.email = "";
  quickContact.company = "";
  quickContactDialog.value = false;
  await patch({ external_assignee_ids: [...task.value.external_assignees.map((c) => c.id), contact.id] });
}

function onLabelsChange(values) {
  const ids = values.map((v) => (typeof v === "object" ? v.id : v));
  patch({ label_ids: ids });
}

async function addSubtask() {
  if (!newSubtask.value.trim() || !task.value) return;
  await taskStore.createTask({
    project: props.project.id,
    column: task.value.column,
    parent: task.value.id,
    title: newSubtask.value.trim(),
  });
  newSubtask.value = "";
}

async function addDependency() {
  if (!pendingDependency.value || !task.value) return;
  await taskStore.addDependency(pendingDependency.value, task.value.id, "FS", pendingBlocking.value);
  pendingDependency.value = null;
  pendingBlocking.value = false;
}

async function removeDependency(id) {
  await taskStore.removeDependency(id);
}

async function toggleBlocking(dep) {
  await taskStore.toggleDependencyBlocking(dep.id, !dep.enforce_blocking);
}

async function remove() {
  if (task.value && confirm("Supprimer cette tache ?")) {
    await taskStore.deleteTask(task.value.id);
    close();
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "";
}
</script>
