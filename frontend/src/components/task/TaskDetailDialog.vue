<template>
  <v-dialog :model-value="modelValue" max-width="1060" @update:model-value="close">
    <v-card v-if="isCreate" density="compact">
      <v-card-title class="text-subtitle-1 py-3">Nouvelle tache</v-card-title>
      <v-divider />
      <v-card-text class="py-3">
        <v-text-field v-model="createForm.title" label="Titre" density="compact" autofocus @keyup.enter="create" />
        <v-row dense>
          <v-col cols="4">
            <v-text-field v-model="createForm.start_date" label="Debut" type="date" density="compact" hide-details />
          </v-col>
          <v-col cols="4">
            <v-text-field
              v-model.number="createForm.duration_days"
              label="Duree (jours)"
              type="number"
              min="1"
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="4">
            <v-text-field
              v-model="createForm.due_date"
              label="Echeance"
              type="date"
              density="compact"
              hide-details
              :disabled="!!createForm.duration_days && !!createForm.start_date"
            />
          </v-col>
        </v-row>
        <p class="text-caption text-medium-emphasis mt-2 mb-0">
          Indiquez une duree pour calculer l'echeance automatiquement.
        </p>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Annuler</v-btn>
        <v-btn color="primary" :disabled="!createForm.title.trim()" @click="create">Creer</v-btn>
      </v-card-actions>
    </v-card>

    <v-card v-else-if="task">
      <div class="d-flex align-center px-4 py-2">
        <v-icon v-if="task.is_milestone" icon="mdi-flag-checkered" color="warning" class="mr-2" />
        <v-text-field
          v-model="task.title"
          variant="plain"
          density="compact"
          hide-details
          class="text-h6 flex-grow-1"
          :readonly="!canEditFull"
          @blur="patch({ title: task.title })"
        />
        <v-chip v-if="task.is_blocked" size="small" color="warning" class="mr-2" prepend-icon="mdi-lock-outline">
          Bloquee
        </v-chip>
        <v-btn
          v-if="canEditFull || canEditState"
          color="primary"
          variant="tonal"
          size="small"
          prepend-icon="mdi-content-save-outline"
          class="mr-2"
          @click="save"
        >
          Enregistrer
        </v-btn>
        <v-btn icon="mdi-close" variant="text" density="comfortable" @click="close" />
      </div>
      <v-divider />

      <v-row no-gutters>
        <v-col cols="12" md="7" class="pane">
          <v-tabs v-model="tab" density="compact" class="px-2">
            <v-tab value="details" density="compact">Details</v-tab>
            <v-tab value="planning" density="compact">Planification</v-tab>
            <v-tab value="links" density="compact">
              Liens
              <v-chip v-if="linksCount" size="x-small" class="ml-1">{{ linksCount }}</v-chip>
            </v-tab>
          </v-tabs>
          <v-divider />

          <v-window v-model="tab" class="pane-body">
            <!-- ---------- DETAILS ---------- -->
            <v-window-item value="details" class="pa-3">
              <v-textarea
                v-model="task.description"
                label="Description"
                variant="outlined"
                rows="2"
                density="compact"
                hide-details
                class="mb-3"
                :readonly="!canEditFull"
                @blur="patch({ description: task.description })"
              />
              <v-row dense>
                <v-col cols="6">
                  <v-select
                    v-model="task.column"
                    :items="project.columns"
                    item-title="name"
                    item-value="id"
                    label="Statut"
                    density="compact"
                    hide-details
                    :readonly="!canEditState"
                    @update:model-value="(v) => patch({ column: v })"
                  />
                </v-col>
                <v-col cols="6">
                  <v-select
                    v-model="task.priority"
                    :items="priorities"
                    label="Priorite"
                    density="compact"
                    hide-details
                    :readonly="!canEditFull"
                    @update:model-value="(v) => patch({ priority: v })"
                  />
                </v-col>
                <v-col cols="6">
                  <v-select
                    v-model="task.assignees"
                    :items="project.members"
                    item-title="first_name"
                    item-value="id"
                    label="Assignes"
                    multiple
                    chips
                    closable-chips
                    return-object
                    density="compact"
                    hide-details
                    :readonly="!canEditFull"
                    @update:model-value="onAssigneesChange"
                  />
                </v-col>
                <v-col cols="6">
                  <div class="d-flex align-center ga-1">
                    <v-select
                      v-model="task.external_assignees"
                      :items="workspaceStore.externalContacts"
                      item-title="name"
                      item-value="id"
                      label="Externes"
                      multiple
                      chips
                      closable-chips
                      return-object
                      density="compact"
                      hide-details
                      :readonly="!canEditFull"
                      @update:model-value="onExternalAssigneesChange"
                    >
                      <template #chip="{ item, props: chipProps }">
                        <v-chip v-bind="chipProps" size="small" prepend-icon="mdi-account-hard-hat-outline">
                          {{ item.raw.name }}
                        </v-chip>
                      </template>
                    </v-select>
                    <v-tooltip location="top" text="Nouveau sous-traitant (notifie par e-mail)">
                      <template #activator="{ props: tipProps }">
                        <v-btn
                          v-if="canEditFull"
                          v-bind="tipProps"
                          icon="mdi-plus"
                          size="x-small"
                          variant="tonal"
                          @click="quickContactDialog = true"
                        />
                      </template>
                    </v-tooltip>
                  </div>
                </v-col>
                <v-col cols="8">
                  <v-select
                    v-model="task.labels"
                    :items="project.labels"
                    item-title="name"
                    item-value="id"
                    label="Etiquettes"
                    multiple
                    chips
                    closable-chips
                    return-object
                    density="compact"
                    hide-details
                    :readonly="!canEditFull"
                    @update:model-value="onLabelsChange"
                  />
                </v-col>
                <v-col cols="4" class="d-flex align-center">
                  <v-checkbox
                    v-model="task.is_milestone"
                    label="Jalon"
                    density="compact"
                    hide-details
                    :readonly="!canEditFull"
                    @change="patch({ is_milestone: task.is_milestone })"
                  />
                </v-col>
                <v-col cols="8">
                  <v-select
                    v-model="task.recurrence"
                    :items="recurrences"
                    label="Recurrence"
                    density="compact"
                    hide-details
                    :readonly="!canEditFull"
                    @update:model-value="(v) => patch({ recurrence: v })"
                  />
                </v-col>
                <v-col cols="12" class="d-flex align-center">
                  <span class="text-caption text-medium-emphasis mr-2">Couleur</span>
                  <input
                    type="color"
                    :value="task.color || DEFAULT_TASK_COLOR"
                    class="color-swatch mr-2"
                    :disabled="!canEditFull"
                    @change="(e) => patch({ color: e.target.value })"
                  />
                  <v-btn v-if="task.color && canEditFull" size="x-small" variant="text" @click="patch({ color: '' })">
                    Reinitialiser
                  </v-btn>
                </v-col>
                <v-col v-if="task.recurrence !== 'none'" cols="12">
                  <v-alert density="compact" variant="tonal" color="info" class="text-caption">
                    <v-icon icon="mdi-repeat" size="14" class="mr-1" />
                    Une fois terminee, une nouvelle occurrence sera creee automatiquement avec les dates decalees
                    ({{ recurrenceLabel }}).
                  </v-alert>
                </v-col>
                <v-col cols="12">
                  <div class="d-flex align-center">
                    <span class="text-caption mr-3">Avancement</span>
                    <v-slider
                      v-model="task.progress"
                      :max="100"
                      step="5"
                      density="compact"
                      hide-details
                      thumb-label
                      :readonly="!canEditState"
                      @end="patch({ progress: task.progress })"
                    />
                    <span class="text-caption ml-3" style="min-width: 34px">{{ task.progress }}%</span>
                  </div>
                </v-col>
              </v-row>

              <template v-if="customFields.length">
                <v-divider class="my-2" />
                <div class="text-caption text-medium-emphasis mb-1">Champs personnalises</div>
                <v-row dense>
                  <v-col v-for="field in customFields" :key="field.id" cols="6">
                    <v-checkbox
                      v-if="field.field_type === 'checkbox'"
                      :model-value="customDraft[field.id] === 'true'"
                      :label="field.name"
                      density="compact"
                      hide-details
                      :readonly="!canEditState"
                      @update:model-value="(v) => saveCustom(field, v ? 'true' : 'false')"
                    />
                    <v-select
                      v-else-if="field.field_type === 'select'"
                      v-model="customDraft[field.id]"
                      :items="field.options"
                      :label="field.name"
                      density="compact"
                      hide-details
                      clearable
                      :readonly="!canEditState"
                      @update:model-value="(v) => saveCustom(field, v)"
                    />
                    <v-text-field
                      v-else
                      v-model="customDraft[field.id]"
                      :label="field.name"
                      :type="inputTypeFor(field)"
                      density="compact"
                      hide-details
                      :readonly="!canEditState"
                      @blur="saveCustom(field, customDraft[field.id])"
                    />
                  </v-col>
                </v-row>
              </template>
            </v-window-item>

            <!-- ---------- PLANIFICATION ---------- -->
            <v-window-item value="planning" class="pa-3">
              <div class="text-caption text-medium-emphasis mb-1">Plan previsionnel</div>
              <v-row dense>
                <v-col cols="4">
                  <v-tooltip :disabled="!task.is_start_locked" location="top" :text="startLockReason">
                    <template #activator="{ props: tipProps }">
                      <div v-bind="tipProps">
                        <v-text-field
                          v-model="task.start_date"
                          label="Debut"
                          type="date"
                          density="compact"
                          hide-details
                          :readonly="!canEditFull || task.is_start_locked"
                          :append-inner-icon="task.is_start_locked ? 'mdi-lock' : undefined"
                          @change="patch({ start_date: task.start_date })"
                        />
                      </div>
                    </template>
                  </v-tooltip>
                </v-col>
                <v-col cols="4">
                  <v-text-field
                    v-model.number="durationDraft"
                    label="Duree (jours)"
                    type="number"
                    min="1"
                    density="compact"
                    hide-details
                    :readonly="!canEditFull"
                    @change="applyDuration"
                  />
                </v-col>
                <v-col cols="4">
                  <v-text-field
                    v-model="task.due_date"
                    label="Echeance"
                    type="date"
                    density="compact"
                    hide-details
                    :readonly="!canEditFull"
                    @change="patch({ due_date: task.due_date })"
                  />
                </v-col>
              </v-row>

              <v-alert
                v-if="task.is_start_locked"
                density="compact"
                variant="tonal"
                color="info"
                class="mt-2 text-caption"
              >
                <v-icon icon="mdi-lock-outline" size="14" class="mr-1" />
                {{ startLockReason }}
              </v-alert>
              <v-alert v-if="patchError" density="compact" variant="tonal" color="error" class="mt-2 text-caption" closable @click:close="patchError = ''">
                {{ patchError }}
              </v-alert>

              <v-divider class="my-3" />
              <div class="d-flex align-center mb-1">
                <span class="text-caption text-medium-emphasis">Suivi reel</span>
                <v-spacer />
                <template v-if="canEditState">
                  <v-tooltip :disabled="!task.is_blocked" location="top">
                    <template #activator="{ props: tipProps }">
                      <span v-bind="tipProps">
                        <v-btn size="x-small" variant="tonal" class="mr-1" :disabled="task.is_blocked" @click="startNow">
                          Demarrer
                        </v-btn>
                      </span>
                    </template>
                    <span>Bloquee par : {{ task.blocking_predecessor_titles.join(", ") }}</span>
                  </v-tooltip>
                  <v-btn size="x-small" variant="tonal" color="success" @click="completeNow">Terminer</v-btn>
                </template>
              </div>
              <v-row dense>
                <v-col cols="6">
                  <v-text-field
                    v-model="task.actual_start_date"
                    label="Debut reel"
                    type="date"
                    density="compact"
                    hide-details
                    :readonly="!canEditState"
                    @change="patch({ actual_start_date: task.actual_start_date || null })"
                  />
                </v-col>
                <v-col cols="6">
                  <v-text-field
                    v-model="task.actual_end_date"
                    label="Fin reelle"
                    type="date"
                    density="compact"
                    hide-details
                    :readonly="!canEditState"
                    @change="patch({ actual_end_date: task.actual_end_date || null })"
                  />
                </v-col>
              </v-row>

              <v-alert v-if="startError" density="compact" variant="tonal" color="error" class="mt-2 text-caption" closable @click:close="startError = ''">
                {{ startError }}
              </v-alert>
              <v-alert v-if="task.is_blocked" density="compact" variant="tonal" color="warning" class="mt-2 text-caption">
                En attente de : {{ task.blocking_predecessor_titles.join(", ") }}
              </v-alert>
              <v-alert v-if="task.baseline_start_date" density="compact" variant="tonal" color="blue-grey" class="mt-2 text-caption">
                Ligne de base : {{ task.baseline_start_date }} &rarr; {{ task.baseline_end_date }}
                <span v-if="varianceLabel"> - {{ varianceLabel }}</span>
              </v-alert>

              <v-divider class="my-3" />
              <TaskTimeTracking :task-id="task.id" :can-track="canEditState" :can-manage-all="canEditFull" />
            </v-window-item>

            <!-- ---------- LIENS ---------- -->
            <v-window-item value="links" class="pa-3">
              <div class="d-flex align-center mb-1">
                <span class="text-caption text-medium-emphasis">Sous-taches ({{ subtasks.length }})</span>
              </div>
              <v-list v-if="subtasks.length" density="compact" class="py-0 bounded-list">
                <v-list-item v-for="s in subtasks" :key="s.id" class="px-2" @click="$emit('open-task', s.id)">
                  <template #prepend>
                    <v-progress-circular :model-value="s.progress" size="18" width="3" color="success" class="mr-2" />
                  </template>
                  <v-list-item-title class="text-body-2">{{ s.title }}</v-list-item-title>
                </v-list-item>
              </v-list>
              <v-text-field
                v-if="canEditFull"
                v-model="newSubtask"
                placeholder="Ajouter une sous-tache puis Entree"
                density="compact"
                hide-details
                variant="outlined"
                class="mt-1"
                @keyup.enter="addSubtask"
              />

              <v-divider class="my-3" />
              <div class="d-flex align-center mb-1">
                <span class="text-caption text-medium-emphasis">Demarre apres</span>
                <v-tooltip location="top" max-width="320">
                  <template #activator="{ props: tipProps }">
                    <v-icon v-bind="tipProps" icon="mdi-help-circle-outline" size="14" class="ml-1" />
                  </template>
                  <span>
                    La fin de la tache precedente fixe le debut de celle-ci. Le cadenas rend le lien bloquant :
                    la tache ne peut alors pas demarrer tant que la precedente n'est pas terminee, et ses assignes
                    sont notifies des qu'elle se libere.
                  </span>
                </v-tooltip>
              </div>
              <div class="mb-2">
                <v-chip
                  v-for="dep in predecessorDeps"
                  :key="dep.id"
                  :closable="canEditFull"
                  size="small"
                  class="mr-1 mb-1"
                  :color="dep.enforce_blocking ? 'warning' : undefined"
                  @click:close="removeDependency(dep.id)"
                >
                  <v-icon
                    :icon="dep.enforce_blocking ? 'mdi-lock' : 'mdi-lock-open-variant-outline'"
                    size="14"
                    class="mr-1"
                    @click.stop="canEditFull && toggleBlocking(dep)"
                  />
                  {{ taskTitle(dep.predecessor) }}
                </v-chip>
                <span v-if="!predecessorDeps.length" class="text-caption text-medium-emphasis">
                  Aucune dependance : le debut est libre.
                </span>
              </div>
              <v-row v-if="canEditFull" dense class="align-center">
                <v-col cols="7">
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
                <v-col cols="3">
                  <v-checkbox v-model="pendingBlocking" label="Bloquante" density="compact" hide-details />
                </v-col>
                <v-col cols="2">
                  <v-btn size="small" variant="tonal" :disabled="!pendingDependency" @click="addDependency">
                    Ajouter
                  </v-btn>
                </v-col>
              </v-row>
              <v-alert v-if="dependencyError" density="compact" variant="tonal" color="error" class="mt-2 text-caption" closable @click:close="dependencyError = ''">
                {{ dependencyError }}
              </v-alert>

              <v-divider class="my-3" />
              <TaskAttachments
                :task-id="task.id"
                :can-edit="canEditState"
                :can-review="canEditFull"
                :can-comment="canComment"
              />
            </v-window-item>
          </v-window>
        </v-col>

        <v-col cols="12" md="5" class="border-s pane">
          <TaskComments :task-id="task.id" :can-comment="canComment" />
        </v-col>
      </v-row>

      <v-divider />
      <v-card-actions class="py-1">
        <v-btn v-if="canEditFull" color="error" variant="text" size="small" prepend-icon="mdi-delete-outline" @click="remove">
          Supprimer
        </v-btn>
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
        <v-text-field v-model="quickContact.name" label="Nom" density="compact" autofocus />
        <v-text-field v-model="quickContact.email" label="E-mail (pour les notifications)" density="compact" />
        <v-text-field v-model="quickContact.company" label="Societe (optionnel)" density="compact" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="quickContactDialog = false">Annuler</v-btn>
        <v-btn color="primary" :disabled="!quickContact.name.trim()" @click="createQuickContact">Ajouter et assigner</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-snackbar v-model="saveSnackbar" :timeout="2000" color="success">Modifications enregistrees.</v-snackbar>
</template>

<script setup>
import TaskAttachments from "@/components/task/TaskAttachments.vue";
import TaskComments from "@/components/task/TaskComments.vue";
import TaskTimeTracking from "@/components/task/TaskTimeTracking.vue";
import { useTaskStore } from "@/stores/task";
import { useWorkspaceStore } from "@/stores/workspace";
import { computed, nextTick, reactive, ref, watch } from "vue";

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
const tab = ref("details");
const newSubtask = ref("");
const pendingDependency = ref(null);
const pendingBlocking = ref(false);
const startError = ref("");
const patchError = ref("");
const dependencyError = ref("");
const quickContactDialog = ref(false);
const quickContact = reactive({ name: "", email: "", company: "" });
const saveSnackbar = ref(false);

const canEditFull = computed(() => task.value?.can_edit_full ?? false);
const canEditState = computed(() => task.value?.can_edit_state ?? false);
const canComment = computed(() => props.project.my_role === "admin" || props.project.my_role === "member");

const customFields = computed(() => props.project.custom_fields || []);
// Local buffer so the inputs stay editable while the value is being typed;
// it is re-synced from the server every time the task changes.
const customDraft = reactive({});
const durationDraft = ref(null);

const priorities = [
  { title: "Basse", value: "low" },
  { title: "Moyenne", value: "medium" },
  { title: "Haute", value: "high" },
  { title: "Urgente", value: "urgent" },
];

const recurrences = [
  { title: "Aucune", value: "none" },
  { title: "Quotidienne", value: "daily" },
  { title: "Hebdomadaire", value: "weekly" },
  { title: "Mensuelle", value: "monthly" },
];

const DEFAULT_TASK_COLOR = "#42A5F5";

const recurrenceLabel = computed(
  () => recurrences.find((r) => r.value === task.value?.recurrence)?.title.toLowerCase() || ""
);

const createForm = reactive({ title: "", start_date: "", due_date: "", duration_days: null });

const subtasks = computed(() => (task.value ? taskStore.subtasksOf(task.value.id) : []));

const predecessorDeps = computed(() =>
  task.value ? taskStore.dependencies.filter((d) => d.successor === task.value.id) : []
);

const linksCount = computed(() => subtasks.value.length + predecessorDeps.value.length);

const dependencyCandidates = computed(() => {
  if (!task.value) return [];
  const existing = new Set(predecessorDeps.value.map((d) => d.predecessor));
  return taskStore.tasks.filter((t) => t.id !== task.value.id && !existing.has(t.id));
});

const startLockReason = computed(() => {
  const driver = task.value?.start_driver;
  if (!driver) return "";
  return `Debut impose par la fin de « ${driver.title} ». Modifiez cette tache-la, ou retirez la dependance.`;
});

const varianceLabel = computed(() => {
  if (!task.value) return "";
  const variance = task.value.end_variance_days;
  if (variance === null || variance === undefined) return "";
  if (variance > 0) return `retard de ${variance} jour(s)`;
  if (variance < 0) return `avance de ${-variance} jour(s)`;
  return "a l'heure";
});

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      createForm.title = "";
      createForm.start_date = "";
      createForm.due_date = "";
      createForm.duration_days = null;
      pendingDependency.value = null;
      pendingBlocking.value = false;
      startError.value = "";
      patchError.value = "";
      dependencyError.value = "";
      quickContactDialog.value = false;
      tab.value = "details";
    }
  }
);

watch(
  task,
  (value) => {
    if (!value) return;
    durationDraft.value = value.duration_days;
    for (const key of Object.keys(customDraft)) delete customDraft[key];
    for (const field of customFields.value) {
      customDraft[field.id] = value.custom_values?.[String(field.id)] ?? "";
    }
  },
  { immediate: true }
);

function taskTitle(id) {
  return taskStore.byId(id)?.title || "?";
}

function inputTypeFor(field) {
  if (field.field_type === "number") return "number";
  if (field.field_type === "date") return "date";
  return "text";
}

function close() {
  emit("update:modelValue", false);
}

async function create() {
  const payload = {
    project: props.project.id,
    column: props.defaultColumn || props.project.columns[0]?.id,
    title: createForm.title,
    start_date: createForm.start_date || null,
    due_date: createForm.due_date || null,
  };
  // A duration is only meaningful with an anchor date; when both are given the
  // backend derives the echeance from start + duration.
  if (createForm.duration_days && createForm.start_date) {
    payload.duration_days = Number(createForm.duration_days);
    payload.due_date = null;
  }
  const task_ = await taskStore.createTask(payload);
  emit("created", task_);
}

async function patch(payload) {
  if (!task.value) return;
  patchError.value = "";
  try {
    await taskStore.updateTask(task.value.id, payload);
  } catch (e) {
    const data = e.response?.data || {};
    patchError.value = data.start_date?.[0] || data.due_date?.[0] || data.detail || "Modification refusee.";
    // Put the rejected fields back to what the server still holds.
    await taskStore.refreshTask(task.value.id);
    durationDraft.value = task.value?.duration_days ?? null;
  }
}

async function save() {
  // Every field already saves itself on change (blur/select) - this button mainly
  // exists so users have something to click instead of the chat's send button.
  // Blurring flushes a title/description edit still sitting in a focused field.
  if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  await nextTick();
  saveSnackbar.value = true;
}

async function saveCustom(field, value) {
  if (!task.value || !canEditState.value) return;
  const next = value ?? "";
  if ((task.value.custom_values?.[String(field.id)] ?? "") === String(next)) return;
  await patch({ custom_field_values: { [field.id]: next } });
}

async function applyDuration() {
  if (!task.value || !canEditFull.value) return;
  const value = Number(durationDraft.value);
  if (!value || value < 1) {
    durationDraft.value = task.value.duration_days;
    return;
  }
  if (value === task.value.duration_days) return;
  await patch({ duration_days: value });
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

function onAssigneesChange(values) {
  patch({ assignee_ids: values.map((v) => (typeof v === "object" ? v.id : v)) });
}

function onExternalAssigneesChange(values) {
  patch({ external_assignee_ids: values.map((v) => (typeof v === "object" ? v.id : v)) });
}

function onLabelsChange(values) {
  patch({ label_ids: values.map((v) => (typeof v === "object" ? v.id : v)) });
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
  dependencyError.value = "";
  try {
    await taskStore.addDependency(pendingDependency.value, task.value.id, "FS", pendingBlocking.value);
    pendingDependency.value = null;
    pendingBlocking.value = false;
    // The link now drives this task's start date - pull the new schedule in.
    await taskStore.fetchTasks(props.project.id);
  } catch (e) {
    dependencyError.value = e.response?.data?.detail || "Impossible d'ajouter cette dependance.";
  }
}

async function removeDependency(id) {
  await taskStore.removeDependency(id);
  await taskStore.fetchTasks(props.project.id);
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

<style scoped>
.pane {
  /* Grows with the window so a taller screen shows more of the form instead of
     scrolling it, while staying bounded on very tall or very short displays. */
  height: clamp(360px, 64vh, 680px);
  display: flex;
  flex-direction: column;
}
.pane-body {
  flex: 1 1 auto;
  overflow-y: auto;
}
.bounded-list {
  max-height: 150px;
  overflow-y: auto;
}
.color-swatch {
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  flex: none;
}
</style>
