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
        <v-avatar v-for="a in item.assignees" :key="a.id" :color="a.avatar_color" size="24" class="ml-n1">
          <span class="text-caption text-white">{{ a.initials }}</span>
        </v-avatar>
      </div>
    </template>
    <template #item.progress="{ item }">
      <v-progress-linear :model-value="item.progress" height="6" rounded color="success" style="width: 100px" />
    </template>
  </v-data-table>
</template>

<script setup>
import { useTaskStore } from "@/stores/task";

const props = defineProps({ project: { type: Object, required: true } });
defineEmits(["open-task"]);

const taskStore = useTaskStore();

const headers = [
  { title: "Tache", key: "title" },
  { title: "Statut", key: "column" },
  { title: "Priorite", key: "priority" },
  { title: "Debut", key: "start_date" },
  { title: "Echeance", key: "due_date" },
  { title: "Assignes", key: "assignees", sortable: false },
  { title: "Avancement", key: "progress" },
];

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
