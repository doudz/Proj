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
            <v-btn size="x-small" variant="tonal" class="mr-1" @click="startNow">Demarrer aujourd'hui</v-btn>
            <v-btn size="x-small" variant="tonal" color="success" @click="completeNow">Terminer aujourd'hui</v-btn>
          </div>
          <p class="text-caption text-medium-emphasis mb-2">
            Les dates reelles sont libres : une tache peut demarrer ou se terminer avant ou apres les dates planifiees ci-dessus.
          </p>
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
          <div class="text-subtitle-2 mb-2">Dependances (a demarrer apres)</div>
          <v-chip
            v-for="dep in predecessorDeps"
            :key="dep.id"
            closable
            size="small"
            class="mr-1 mb-1"
            @click:close="removeDependency(dep.id)"
          >
            {{ taskTitle(dep.predecessor) }}
          </v-chip>
          <v-autocomplete
            :items="dependencyCandidates"
            item-title="title"
            item-value="id"
            label="Ajouter une dependance"
            density="compact"
            hide-details
            variant="outlined"
            @update:model-value="addDependency"
          />
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
</template>

<script setup>
import TaskComments from "@/components/task/TaskComments.vue";
import { useTaskStore } from "@/stores/task";
import { computed, reactive, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  taskId: { type: [String, Number], default: null },
  project: { type: Object, required: true },
  defaultColumn: { type: [String, Number], default: null },
});
const emit = defineEmits(["update:modelValue", "open-task", "created"]);

const taskStore = useTaskStore();
const isCreate = computed(() => props.modelValue && !props.taskId);
const task = computed(() => (props.taskId ? taskStore.byId(Number(props.taskId)) : null));
const newSubtask = ref("");

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
  if (task.value) await taskStore.startTask(task.value.id);
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

async function addDependency(predecessorId) {
  if (!predecessorId || !task.value) return;
  await taskStore.addDependency(predecessorId, task.value.id);
}

async function removeDependency(id) {
  await taskStore.removeDependency(id);
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
