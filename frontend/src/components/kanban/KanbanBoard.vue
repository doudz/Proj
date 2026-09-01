<template>
  <div class="d-flex ga-4 kanban-scroll">
    <div v-for="column in sortedColumns" :key="column.id" class="kanban-column">
      <div class="d-flex align-center mb-2 px-1">
        <span class="dot mr-2" :style="{ backgroundColor: column.color }"></span>
        <span class="text-subtitle-2 font-weight-bold">{{ column.name }}</span>
        <v-chip size="x-small" class="ml-2">{{ tasksByColumn[column.id]?.length || 0 }}</v-chip>
        <v-spacer />
        <v-btn v-if="isAdmin" icon="mdi-plus" size="x-small" variant="text" @click="$emit('create-task', column.id)" />
      </div>
      <draggable
        :list="tasksByColumn[column.id] || []"
        group="tasks"
        item-key="id"
        class="kanban-drop-zone"
        ghost-class="ghost-card"
        filter=".no-drag"
        :prevent-on-filter="false"
        @change="(e) => onChange(e, column.id)"
      >
        <template #item="{ element }">
          <TaskCard :task="element" :class="{ 'no-drag': !element.can_edit_state }" @click="$emit('open-task', element.id)" />
        </template>
      </draggable>
    </div>
  </div>
</template>

<script setup>
import TaskCard from "@/components/kanban/TaskCard.vue";
import { useTaskStore } from "@/stores/task";
import { computed } from "vue";
import draggable from "vuedraggable";

const props = defineProps({ project: { type: Object, required: true } });
defineEmits(["open-task", "create-task"]);

const taskStore = useTaskStore();

const isAdmin = computed(() => props.project.my_role === "admin");

const sortedColumns = computed(() => [...props.project.columns].sort((a, b) => a.order - b.order));

const tasksByColumn = computed(() => {
  const map = {};
  for (const task of taskStore.rootTasks) {
    if (!map[task.column]) map[task.column] = [];
    map[task.column].push(task);
  }
  return map;
});

function onChange(event, columnId) {
  if (event.added) {
    taskStore.moveTask(event.added.element.id, columnId, event.added.newIndex);
  } else if (event.moved) {
    taskStore.moveTask(event.moved.element.id, columnId, event.moved.newIndex);
  }
}
</script>

<style scoped>
.kanban-scroll {
  overflow-x: auto;
  min-height: 70vh;
}
.kanban-column {
  min-width: 280px;
  max-width: 280px;
}
.kanban-drop-zone {
  min-height: 60px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
  padding: 4px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.ghost-card {
  opacity: 0.4;
}
</style>
