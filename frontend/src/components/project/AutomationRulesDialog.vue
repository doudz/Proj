<template>
  <v-dialog :model-value="modelValue" max-width="640" scrollable @update:model-value="close">
    <v-card title="Regles d'automatisation">
      <v-card-subtitle class="px-4">
        "Quand X arrive, fais Y." Les regles s'appliquent des qu'une tache change, dans l'ordre ou elles sont
        listees.
      </v-card-subtitle>
      <v-card-text>
        <v-list v-if="rules.length" density="comfortable">
          <v-list-item v-for="rule in rules" :key="rule.id" class="rule-row">
            <v-list-item-title class="d-flex align-center">
              <v-switch
                :model-value="rule.enabled"
                density="compact"
                hide-details
                color="primary"
                class="flex-grow-0 mr-2"
                @update:model-value="(v) => toggleEnabled(rule, v)"
              />
              <span :class="{ 'text-medium-emphasis': !rule.enabled }">{{ rule.name }}</span>
              <v-spacer />
              <v-btn icon="mdi-delete-outline" variant="text" size="small" @click="remove(rule)" />
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              Quand {{ triggerLabel(rule) }} &rarr; {{ actionLabel(rule) }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
        <p v-else class="text-medium-emphasis">Aucune regle pour le moment.</p>

        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">Nouvelle regle</div>
        <v-text-field v-model="draft.name" label="Nom" density="compact" hide-details class="mb-2" />

        <v-row dense>
          <v-col cols="6">
            <v-select v-model="draft.trigger" :items="triggers" label="Quand" density="compact" hide-details />
          </v-col>
          <v-col cols="6">
            <v-select
              v-if="draft.trigger === 'column_changed'"
              v-model="draft.trigger_column"
              :items="project.columns"
              item-title="name"
              item-value="id"
              label="Colonne"
              density="compact"
              hide-details
            />
          </v-col>
        </v-row>

        <v-row dense class="mt-1">
          <v-col cols="6">
            <v-select v-model="draft.action" :items="actions" label="Faire" density="compact" hide-details />
          </v-col>
          <v-col cols="6">
            <v-select
              v-if="draft.action === 'move_to_column'"
              v-model="draft.action_column"
              :items="project.columns"
              item-title="name"
              item-value="id"
              label="Vers la colonne"
              density="compact"
              hide-details
            />
            <v-select
              v-else-if="draft.action === 'set_priority'"
              v-model="draft.action_priority"
              :items="priorities"
              label="Nouvelle priorite"
              density="compact"
              hide-details
            />
            <v-select
              v-else-if="draft.action === 'add_label'"
              v-model="draft.action_label"
              :items="project.labels"
              item-title="name"
              item-value="id"
              label="Etiquette"
              density="compact"
              hide-details
            />
          </v-col>
        </v-row>

        <v-alert v-if="error" type="error" density="compact" variant="tonal" class="mt-2">{{ error }}</v-alert>
        <v-btn color="primary" class="mt-3" :disabled="!draft.name.trim()" @click="create">Ajouter</v-btn>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Fermer</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { useProjectStore } from "@/stores/project";
import { computed, reactive, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  project: { type: Object, required: true },
});
const emit = defineEmits(["update:modelValue"]);

const projectStore = useProjectStore();
const error = ref("");

const triggers = [
  { title: "une tache est creee", value: "task_created" },
  { title: "une tache est deplacee dans une colonne", value: "column_changed" },
  { title: "une tache est terminee (100%)", value: "task_completed" },
];
const actions = [
  { title: "deplacer vers une colonne", value: "move_to_column" },
  { title: "changer la priorite", value: "set_priority" },
  { title: "ajouter une etiquette", value: "add_label" },
  { title: "notifier les assignes", value: "notify_assignees" },
];
const priorities = [
  { title: "Basse", value: "low" },
  { title: "Moyenne", value: "medium" },
  { title: "Haute", value: "high" },
  { title: "Urgente", value: "urgent" },
];

const draft = reactive({
  name: "",
  trigger: "task_created",
  trigger_column: null,
  action: "notify_assignees",
  action_column: null,
  action_priority: null,
  action_label: null,
});

const rules = computed(() => projectStore.automationRules);

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      error.value = "";
      resetDraft();
      await projectStore.fetchAutomationRules(props.project.id);
    }
  }
);

function resetDraft() {
  draft.name = "";
  draft.trigger = "task_created";
  draft.trigger_column = null;
  draft.action = "notify_assignees";
  draft.action_column = null;
  draft.action_priority = null;
  draft.action_label = null;
}

function columnName(id) {
  return props.project.columns.find((c) => c.id === id)?.name || "?";
}

function labelName(id) {
  return props.project.labels.find((l) => l.id === id)?.name || "?";
}

function triggerLabel(rule) {
  if (rule.trigger === "column_changed") return `deplacee dans « ${columnName(rule.trigger_column)} »`;
  return triggers.find((t) => t.value === rule.trigger)?.title || rule.trigger;
}

function actionLabel(rule) {
  if (rule.action === "move_to_column") return `deplacer vers « ${columnName(rule.action_column)} »`;
  if (rule.action === "set_priority") return `priorite -> ${priorities.find((p) => p.value === rule.action_priority)?.title}`;
  if (rule.action === "add_label") return `ajouter l'etiquette « ${labelName(rule.action_label)} »`;
  return "notifier les assignes";
}

function close() {
  emit("update:modelValue", false);
}

async function create() {
  error.value = "";
  // action_priority is a plain CharField (not nullable in the database, only
  // blankable), so it must travel as "" rather than null when unused - only
  // the two FK-backed fields accept an explicit null.
  const payload = {
    project: props.project.id,
    name: draft.name,
    trigger: draft.trigger,
    trigger_column: draft.trigger === "column_changed" ? draft.trigger_column : null,
    action: draft.action,
    action_column: draft.action === "move_to_column" ? draft.action_column : null,
    action_priority: draft.action === "set_priority" ? draft.action_priority || "" : "",
    action_label: draft.action === "add_label" ? draft.action_label : null,
  };
  try {
    await projectStore.createAutomationRule(payload);
    resetDraft();
  } catch (e) {
    const data = e.response?.data || {};
    error.value = Object.values(data).flat().join(" ") || "Impossible de creer cette regle.";
  }
}

async function toggleEnabled(rule, value) {
  await projectStore.updateAutomationRule(rule.id, { enabled: value });
}

async function remove(rule) {
  if (confirm(`Supprimer la regle "${rule.name}" ?`)) {
    await projectStore.deleteAutomationRule(rule.id);
  }
}
</script>

<style scoped>
.rule-row {
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
</style>
