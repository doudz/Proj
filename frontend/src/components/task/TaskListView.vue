<template>
  <v-data-table
    :headers="headers"
    :items="taskStore.tasks"
    :items-per-page="50"
    density="comfortable"
    @click:row="(_, { item }) => $emit('open-task', item.id)"
  >
    <template #item.title="{ item }">
      <span :style="{ paddingLeft: item.parent ? '24px' : '0' }">
        <v-icon v-if="item.parent" icon="mdi-subdirectory-arrow-right" size="14" class="mr-1" />
        {{ item.title }}
      </span>
    </template>
    <template #item.column="{ item }">
      <v-chip size="small" :color="columnColor(item.column)">{{ columnName(item.column) }}</v-chip>
    </template>
    <template #item.priority="{ item }">
      <v-chip size="small" :color="priorityColor(item.priority)" variant="tonal">{{ priorityLabel(item.priority) }}</v-chip>
    </template>
    <template #item.assignees="{ item }">
      <div class="d-flex ml-n1">
        <v-avatar v-for="a in item.assignees" :key="a.id" :color="a.avatar_color" size="24" class="ml-n1" :title="a.first_name + ' ' + a.last_name">
          <span class="text-caption text-white">{{ a.initials }}</span>
        </v-avatar>
        <v-avatar
          v-for="c in item.external_assignees"
          :key="'ext-' + c.id"
          :color="c.color"
          size="24"
          class="ml-n1 external-avatar"
          :title="c.name + ' (externe)'"
        >
          <span class="text-caption text-white">{{ c.initials }}</span>
        </v-avatar>
      </div>
    </template>
    <template #item.progress="{ item }">
      <v-progress-linear :model-value="item.progress" height="6" rounded color="success" style="width: 100px" />
    </template>
    <template v-for="field in listCustomFields" :key="field.id" #[`item.cf_${field.id}`]="{ item }">
      <span v-if="field.field_type === 'checkbox'">
        <v-icon
          :icon="item.custom_values?.[field.id] === 'true' ? 'mdi-check' : 'mdi-minus'"
          size="16"
          :color="item.custom_values?.[field.id] === 'true' ? 'success' : 'grey'"
        />
      </span>
      <span v-else-if="item.custom_values?.[field.id]">{{ item.custom_values[field.id] }}</span>
      <span v-else class="text-medium-emphasis">-</span>
    </template>
    <template #item.actual_end_date="{ item }">
      <span v-if="item.actual_end_date">{{ item.actual_end_date }}</span>
      <span v-else-if="item.actual_start_date" class="text-medium-emphasis">en cours</span>
      <span v-else class="text-medium-emphasis">-</span>
    </template>
    <template #item.variance="{ item }">
      <v-chip v-if="item.end_variance_days > 0" size="small" color="error" variant="tonal">+{{ item.end_variance_days }} j</v-chip>
      <v-chip v-else-if="item.end_variance_days < 0" size="small" color="success" variant="tonal">{{ item.end_variance_days }} j</v-chip>
      <v-chip v-else-if="item.end_variance_days === 0" size="small" color="grey" variant="tonal">a l'heure</v-chip>
      <span v-else class="text-medium-emphasis">-</span>
    </template>
  </v-data-table>
</template>

<script setup>
import { useTaskStore } from "@/stores/task";
import { computed } from "vue";

const props = defineProps({ project: { type: Object, required: true } });
defineEmits(["open-task"]);

const taskStore = useTaskStore();

const listCustomFields = computed(() => (props.project.custom_fields || []).filter((f) => f.show_in_list));

const headers = computed(() => [
  { title: "Tache", key: "title" },
  { title: "Statut", key: "column" },
  { title: "Priorite", key: "priority" },
  { title: "Debut", key: "start_date" },
  { title: "Echeance", key: "due_date" },
  { title: "Duree", key: "duration_days" },
  { title: "Fin reelle", key: "actual_end_date" },
  { title: "Ecart / ligne de base", key: "variance", sortable: false },
  { title: "Assignes", key: "assignees", sortable: false },
  { title: "Avancement", key: "progress" },
  ...listCustomFields.value.map((f) => ({ title: f.name, key: `cf_${f.id}`, sortable: false })),
]);

const priorityLabels = { low: "Basse", medium: "Moyenne", high: "Haute", urgent: "Urgente" };
const priorityColors = { low: "grey", medium: "info", high: "warning", urgent: "error" };

function priorityLabel(p) {
  return priorityLabels[p] || p;
}
function priorityColor(p) {
  return priorityColors[p] || "grey";
}
function columnName(id) {
  return props.project.columns.find((c) => c.id === id)?.name || "-";
}
function columnColor(id) {
  return props.project.columns.find((c) => c.id === id)?.color || "grey";
}
</script>

<style scoped>
.external-avatar {
  border: 2px dashed white;
}
</style>
