<template>
  <v-dialog :model-value="modelValue" max-width="480" @update:model-value="close">
    <v-card title="Informations du projet">
      <v-card-subtitle v-if="!fields.length" class="px-4">
        Aucun champ personnalise de niveau "Projet" pour le moment. Ajoutez-en depuis « Champs personnalises »
        (menu <v-icon icon="mdi-dots-vertical" size="14" />) en choisissant le niveau "Projet".
      </v-card-subtitle>
      <v-card-text v-else>
        <v-row dense>
          <v-col v-for="field in fields" :key="field.id" cols="12">
            <v-checkbox
              v-if="field.field_type === 'checkbox'"
              :model-value="draft[field.id] === 'true'"
              :label="field.name"
              density="compact"
              hide-details
              :readonly="!canEdit"
              @update:model-value="(v) => save(field, v ? 'true' : 'false')"
            />
            <v-switch
              v-else-if="field.field_type === 'switch'"
              :model-value="draft[field.id] === 'true'"
              :label="field.name"
              density="compact"
              hide-details
              color="primary"
              :readonly="!canEdit"
              @update:model-value="(v) => save(field, v ? 'true' : 'false')"
            />
            <v-select
              v-else-if="field.field_type === 'select'"
              v-model="draft[field.id]"
              :items="field.options"
              :label="field.name"
              density="compact"
              hide-details
              clearable
              :readonly="!canEdit"
              @update:model-value="(v) => save(field, v)"
            />
            <v-text-field
              v-else
              v-model="draft[field.id]"
              :label="field.name"
              :type="inputTypeFor(field)"
              density="compact"
              hide-details
              :readonly="!canEdit"
              @blur="save(field, draft[field.id])"
            />
          </v-col>
        </v-row>
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
import { computed, reactive, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  project: { type: Object, required: true },
});
const emit = defineEmits(["update:modelValue"]);

const projectStore = useProjectStore();
const draft = reactive({});

const fields = computed(() => (props.project.custom_fields || []).filter((f) => f.level === "project"));
const canEdit = computed(() => props.project.my_role === "admin");

function inputTypeFor(field) {
  if (field.field_type === "number") return "number";
  if (field.field_type === "date") return "date";
  if (field.field_type === "url") return "url";
  return "text";
}

watch(
  () => props.project.custom_values,
  () => {
    for (const key of Object.keys(draft)) delete draft[key];
    for (const field of fields.value) {
      draft[field.id] = props.project.custom_values?.[String(field.id)] ?? "";
    }
  },
  { immediate: true }
);

function close() {
  emit("update:modelValue", false);
}

async function save(field, value) {
  if (!canEdit.value) return;
  const next = value ?? "";
  if ((props.project.custom_values?.[String(field.id)] ?? "") === String(next)) return;
  await projectStore.updateProject(props.project.id, { custom_field_values: { [field.id]: next } });
}
</script>
