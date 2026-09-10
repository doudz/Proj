<template>
  <v-dialog :model-value="modelValue" max-width="620" scrollable @update:model-value="close">
    <v-card title="Champs personnalises">
      <v-card-subtitle class="px-4">
        Ajoutez vos propres informations aux taches ou au projet lui-meme (client, budget, phase...). Un champ de
        tache apparait dans le detail de chaque tache (et peut etre masque au cas par cas) ; un champ de projet
        apparait dans l'entete du projet.
      </v-card-subtitle>
      <v-card-text>
        <template v-if="taskFields.length">
          <div class="text-subtitle-2 mb-1">Champs de tache</div>
          <v-list density="comfortable" class="mb-2">
            <v-list-item v-for="field in taskFields" :key="field.id">
              <template #prepend>
                <v-icon :icon="typeIcon(field.field_type)" class="mr-2" />
              </template>
              <v-list-item-title>
                <v-text-field
                  v-model="field.name"
                  variant="plain"
                  density="compact"
                  hide-details
                  class="field-name-input"
                  @blur="renameField(field)"
                  @keyup.enter="(e) => e.target.blur()"
                />
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ typeLabel(field.field_type) }}
                <span v-if="field.field_type === 'select' && field.options.length">
                  : {{ field.options.join(", ") }}
                </span>
              </v-list-item-subtitle>
              <template #append>
                <v-tooltip location="top" text="Afficher comme colonne dans la vue liste">
                  <template #activator="{ props: tipProps }">
                    <v-btn
                      v-bind="tipProps"
                      :icon="field.show_in_list ? 'mdi-table-eye' : 'mdi-table-eye-off'"
                      :color="field.show_in_list ? 'primary' : undefined"
                      variant="text"
                      size="small"
                      @click="toggleInList(field)"
                    />
                  </template>
                </v-tooltip>
                <v-btn icon="mdi-delete-outline" variant="text" size="small" @click="remove(field)" />
              </template>
            </v-list-item>
          </v-list>
        </template>

        <template v-if="projectFields.length">
          <div class="text-subtitle-2 mb-1">Champs de projet</div>
          <v-list density="comfortable" class="mb-2">
            <v-list-item v-for="field in projectFields" :key="field.id">
              <template #prepend>
                <v-icon :icon="typeIcon(field.field_type)" class="mr-2" />
              </template>
              <v-list-item-title>
                <v-text-field
                  v-model="field.name"
                  variant="plain"
                  density="compact"
                  hide-details
                  class="field-name-input"
                  @blur="renameField(field)"
                  @keyup.enter="(e) => e.target.blur()"
                />
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ typeLabel(field.field_type) }}
                <span v-if="field.field_type === 'select' && field.options.length">
                  : {{ field.options.join(", ") }}
                </span>
              </v-list-item-subtitle>
              <template #append>
                <v-btn icon="mdi-delete-outline" variant="text" size="small" @click="remove(field)" />
              </template>
            </v-list-item>
          </v-list>
        </template>

        <p v-if="!fields.length" class="text-medium-emphasis">Aucun champ personnalise pour le moment.</p>

        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">Nouveau champ</div>
        <v-row no-gutters class="ga-2">
          <v-col cols="12" sm="6">
            <v-text-field v-model="draft.name" label="Nom" density="compact" hide-details />
          </v-col>
          <v-col cols="6" sm="3">
            <v-select v-model="draft.field_type" :items="fieldTypes" label="Type" density="compact" hide-details />
          </v-col>
          <v-col cols="6" sm="3">
            <v-select v-model="draft.level" :items="levels" label="Niveau" density="compact" hide-details />
          </v-col>
        </v-row>
        <v-text-field
          v-if="draft.field_type === 'select'"
          v-model="draft.optionsText"
          label="Choix possibles (separes par des virgules)"
          density="compact"
          class="mt-2"
          hide-details
        />
        <v-checkbox
          v-if="draft.level === 'task'"
          v-model="draft.show_in_list"
          label="Afficher comme colonne dans la vue liste"
          density="compact"
          hide-details
          class="mt-1"
        />
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
const draft = reactive({ name: "", field_type: "text", level: "task", optionsText: "", show_in_list: false });

const fieldTypes = [
  { title: "Texte", value: "text" },
  { title: "Nombre", value: "number" },
  { title: "Date", value: "date" },
  { title: "Liste de choix", value: "select" },
  { title: "Case a cocher", value: "checkbox" },
  { title: "Interrupteur (Oui/Non)", value: "switch" },
  { title: "Lien", value: "url" },
];

const levels = [
  { title: "Tache", value: "task" },
  { title: "Projet", value: "project" },
];

const typeIcons = {
  text: "mdi-format-text",
  number: "mdi-numeric",
  date: "mdi-calendar-outline",
  select: "mdi-format-list-bulleted",
  checkbox: "mdi-checkbox-marked-outline",
  switch: "mdi-toggle-switch-outline",
  url: "mdi-link-variant",
};

const fields = computed(() => props.project.custom_fields || []);
const taskFields = computed(() => fields.value.filter((f) => f.level !== "project"));
const projectFields = computed(() => fields.value.filter((f) => f.level === "project"));

function typeLabel(value) {
  return fieldTypes.find((t) => t.value === value)?.title || value;
}

function typeIcon(value) {
  return typeIcons[value] || "mdi-form-textbox";
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      draft.name = "";
      draft.field_type = "text";
      draft.level = "task";
      draft.optionsText = "";
      draft.show_in_list = false;
      error.value = "";
    }
  }
);

function close() {
  emit("update:modelValue", false);
}

async function create() {
  error.value = "";
  const options =
    draft.field_type === "select"
      ? draft.optionsText.split(",").map((o) => o.trim()).filter(Boolean)
      : [];
  if (draft.field_type === "select" && !options.length) {
    error.value = "Indiquez au moins un choix possible.";
    return;
  }
  try {
    await projectStore.createCustomField({
      project: props.project.id,
      name: draft.name.trim(),
      field_type: draft.field_type,
      level: draft.level,
      options,
      show_in_list: draft.level === "task" && draft.show_in_list,
      order: fields.value.length,
    });
    draft.name = "";
    draft.optionsText = "";
    draft.show_in_list = false;
  } catch (e) {
    error.value = e.response?.data?.name?.[0] || e.response?.data?.detail || "Impossible de creer ce champ.";
  }
}

async function renameField(field) {
  const name = field.name.trim();
  if (!name) {
    error.value = "Le nom du champ ne peut pas etre vide.";
    await projectStore.fetchProject(props.project.id);
    return;
  }
  try {
    error.value = "";
    await projectStore.updateCustomField(field.id, { name });
  } catch (e) {
    error.value = e.response?.data?.name?.[0] || "Impossible de renommer ce champ.";
    await projectStore.fetchProject(props.project.id);
  }
}

async function toggleInList(field) {
  await projectStore.updateCustomField(field.id, { show_in_list: !field.show_in_list });
}

async function remove(field) {
  if (confirm(`Supprimer le champ "${field.name}" ? Les valeurs saisies seront perdues.`)) {
    await projectStore.deleteCustomField(field.id);
  }
}
</script>

<style scoped>
.field-name-input {
  margin-top: -6px;
}
</style>
