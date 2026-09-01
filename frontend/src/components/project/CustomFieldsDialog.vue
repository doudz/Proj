<template>
  <v-dialog :model-value="modelValue" max-width="620" scrollable @update:model-value="close">
    <v-card title="Champs personnalises">
      <v-card-subtitle class="px-4">
        Ajoutez vos propres informations aux taches de ce projet (client, budget, phase...). Elles apparaissent dans
        le detail de chaque tache et sont interrogeables dans la recherche.
      </v-card-subtitle>
      <v-card-text>
        <v-list v-if="fields.length" density="comfortable">
          <v-list-item v-for="field in fields" :key="field.id">
            <template #prepend>
              <v-icon :icon="typeIcon(field.field_type)" class="mr-2" />
            </template>
            <v-list-item-title>{{ field.name }}</v-list-item-title>
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
        <p v-else class="text-medium-emphasis">Aucun champ personnalise pour le moment.</p>

        <v-divider class="my-3" />
        <div class="text-subtitle-2 mb-2">Nouveau champ</div>
        <v-row no-gutters class="ga-2">
          <v-col cols="12" sm="6">
            <v-text-field v-model="draft.name" label="Nom" density="compact" hide-details />
          </v-col>
          <v-col cols="12" sm="5">
            <v-select v-model="draft.field_type" :items="fieldTypes" label="Type" density="compact" hide-details />
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
const draft = reactive({ name: "", field_type: "text", optionsText: "", show_in_list: false });

const fieldTypes = [
  { title: "Texte", value: "text" },
  { title: "Nombre", value: "number" },
  { title: "Date", value: "date" },
  { title: "Liste de choix", value: "select" },
  { title: "Case a cocher", value: "checkbox" },
  { title: "Lien", value: "url" },
];

const typeIcons = {
  text: "mdi-format-text",
  number: "mdi-numeric",
  date: "mdi-calendar-outline",
  select: "mdi-format-list-bulleted",
  checkbox: "mdi-checkbox-marked-outline",
  url: "mdi-link-variant",
};

const fields = computed(() => props.project.custom_fields || []);

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
      options,
      show_in_list: draft.show_in_list,
      order: fields.value.length,
    });
    draft.name = "";
    draft.optionsText = "";
    draft.show_in_list = false;
  } catch (e) {
    error.value = e.response?.data?.name?.[0] || e.response?.data?.detail || "Impossible de creer ce champ.";
  }
}

async function toggleInList(field) {
  await projectStore.updateCustomField(field.id, { show_in_list: !field.show_in_list });
}

async function remove(field) {
  if (confirm(`Supprimer le champ "${field.name}" ? Les valeurs saisies sur les taches seront perdues.`)) {
    await projectStore.deleteCustomField(field.id);
  }
}
</script>
