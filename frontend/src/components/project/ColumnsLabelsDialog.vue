<template>
  <v-dialog :model-value="modelValue" max-width="640" scrollable @update:model-value="close">
    <v-card title="Colonnes et etiquettes">
      <v-tabs v-model="tab" density="compact">
        <v-tab value="columns">Colonnes</v-tab>
        <v-tab value="labels">Etiquettes</v-tab>
      </v-tabs>
      <v-divider />
      <v-card-text>
        <v-window v-model="tab">
          <v-window-item value="columns">
            <p class="text-caption text-medium-emphasis mb-2">
              Glissez pour reordonner. Supprimer une colonne ne supprime pas ses taches : elles se retrouvent sans
              statut.
            </p>
            <draggable :list="localColumns" item-key="id" handle=".col-handle" @change="onColumnReorder">
              <template #item="{ element }">
                <div class="d-flex align-center py-1">
                  <v-icon icon="mdi-drag-vertical" class="col-handle mr-1" style="cursor: grab" />
                  <input v-model="element.color" type="color" class="color-swatch mr-2" @change="saveColumn(element)" />
                  <v-text-field
                    v-model="element.name"
                    density="compact"
                    variant="plain"
                    hide-details
                    class="flex-grow-1"
                    @blur="saveColumn(element)"
                    @keyup.enter="saveColumn(element)"
                  />
                  <v-tooltip location="top" text="Colonne « termine » : marque les taches a 100%">
                    <template #activator="{ props: tipProps }">
                      <v-checkbox
                        v-bind="tipProps"
                        v-model="element.is_done_column"
                        density="compact"
                        hide-details
                        class="flex-grow-0 mr-1"
                        @change="saveColumn(element)"
                      />
                    </template>
                  </v-tooltip>
                  <v-btn icon="mdi-delete-outline" variant="text" size="small" @click="removeColumn(element)" />
                </div>
              </template>
            </draggable>
            <v-divider class="my-3" />
            <div class="d-flex align-center ga-2">
              <v-text-field
                v-model="newColumnName"
                placeholder="Nouvelle colonne"
                density="compact"
                hide-details
                @keyup.enter="addColumn"
              />
              <v-btn color="primary" size="small" :disabled="!newColumnName.trim()" @click="addColumn">Ajouter</v-btn>
            </div>
          </v-window-item>

          <v-window-item value="labels">
            <v-list density="compact">
              <v-list-item v-for="label in project.labels" :key="label.id" class="px-0">
                <template #prepend>
                  <input
                    :value="label.color"
                    type="color"
                    class="color-swatch mr-2"
                    @change="(e) => saveLabel(label, { color: e.target.value })"
                  />
                </template>
                <v-text-field
                  :model-value="label.name"
                  density="compact"
                  variant="plain"
                  hide-details
                  @update:model-value="(v) => (label.name = v)"
                  @blur="saveLabel(label, { name: label.name })"
                  @keyup.enter="saveLabel(label, { name: label.name })"
                />
                <template #append>
                  <v-btn icon="mdi-delete-outline" variant="text" size="small" @click="removeLabel(label)" />
                </template>
              </v-list-item>
            </v-list>
            <p v-if="!project.labels.length" class="text-caption text-medium-emphasis">Aucune etiquette.</p>
            <v-divider class="my-3" />
            <div class="d-flex align-center ga-2">
              <input v-model="newLabelColor" type="color" class="color-swatch" />
              <v-text-field
                v-model="newLabelName"
                placeholder="Nouvelle etiquette"
                density="compact"
                hide-details
                @keyup.enter="addLabel"
              />
              <v-btn color="primary" size="small" :disabled="!newLabelName.trim()" @click="addLabel">Ajouter</v-btn>
            </div>
          </v-window-item>
        </v-window>
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
import { ref, watch } from "vue";
import draggable from "vuedraggable";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  project: { type: Object, required: true },
});
const emit = defineEmits(["update:modelValue"]);

const projectStore = useProjectStore();
const tab = ref("columns");
const newColumnName = ref("");
const newLabelName = ref("");
const newLabelColor = ref("#7E57C2");

// A plain local array vuedraggable can splice directly for the drag gesture;
// items are the same reactive objects as project.columns, so editing a field
// in place (like everywhere else in this app) still updates the real data.
const localColumns = ref([]);

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      tab.value = "columns";
      newColumnName.value = "";
      newLabelName.value = "";
      newLabelColor.value = "#7E57C2";
      localColumns.value = [...props.project.columns].sort((a, b) => a.order - b.order);
    }
  }
);

function close() {
  emit("update:modelValue", false);
}

async function saveColumn(column) {
  await projectStore.updateColumn(column.id, {
    name: column.name,
    color: column.color,
    is_done_column: column.is_done_column,
  });
}

async function addColumn() {
  if (!newColumnName.value.trim()) return;
  await projectStore.createColumn({
    project: props.project.id,
    name: newColumnName.value.trim(),
    order: props.project.columns.length,
  });
  localColumns.value = [...props.project.columns].sort((a, b) => a.order - b.order);
  newColumnName.value = "";
}

async function removeColumn(column) {
  if (confirm(`Supprimer la colonne "${column.name}" ? Les taches qu'elle contient perdront leur statut.`)) {
    await projectStore.deleteColumn(column.id);
    localColumns.value = localColumns.value.filter((c) => c.id !== column.id);
  }
}

async function onColumnReorder() {
  const order = localColumns.value.map((c) => c.id);
  await projectStore.reorderColumns(props.project.id, order);
}

async function saveLabel(label, payload) {
  await projectStore.updateLabel(label.id, payload);
}

async function addLabel() {
  if (!newLabelName.value.trim()) return;
  await projectStore.createLabel({
    project: props.project.id,
    name: newLabelName.value.trim(),
    color: newLabelColor.value,
  });
  newLabelName.value = "";
}

async function removeLabel(label) {
  if (confirm(`Supprimer l'etiquette "${label.name}" ?`)) {
    await projectStore.deleteLabel(label.id);
  }
}
</script>

<style scoped>
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
